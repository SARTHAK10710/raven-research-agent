"""S3-compatible object storage through boto3 (7.1 section 24.1; 7.2 sections 10-11).

* Owner check before any network call.
* Content is hashed while it streams to the store; a size or SHA-256 mismatch
  deletes the object and raises :class:`ObjectIntegrityError`. The checksum is
  kept as object metadata and checked again on every read.
* Large content goes up in parts (``multipart_threshold_bytes``). A failed part
  upload aborts the multipart upload, so no partial object becomes visible;
  :meth:`S3ObjectStorage.abort_incomplete_uploads` cleans up after crashes.
* boto3 and botocore errors become :class:`ObjectStorageError` with a fixed,
  content-free message; the original is chained for diagnosis.
"""

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, BinaryIO

import boto3
from boto3.exceptions import S3UploadFailedError
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from memory_engine.config import ObjectStorageSettings
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.object_storage import (
    StoredObject,
    require_key_in_scope,
    require_sha256,
)
from memory_engine.exceptions import ObjectIntegrityError, ObjectStorageError, RecordNotFoundError

CHECKSUM_METADATA = "sha256"
_NOT_FOUND_CODES = frozenset({"404", "NoSuchKey", "NotFound"})


class _VerifyingReader:
    """Wraps the caller's stream, hashing and counting bytes as boto3 reads them.

    It exposes ``read`` only, so boto3 treats it as non-seekable and reads each
    byte exactly once.
    """

    def __init__(self, data: BinaryIO) -> None:
        self._data = data
        self._hash = hashlib.sha256()
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._data.read(size)
        self._hash.update(chunk)
        self.size += len(chunk)
        return chunk

    @property
    def sha256(self) -> str:
        return self._hash.hexdigest()


def _is_not_found(err: ClientError) -> bool:
    code = str(err.response.get("Error", {}).get("Code", ""))
    return code in _NOT_FOUND_CODES


@contextmanager
def _storage_errors(operation: str) -> Iterator[None]:
    """Translate client failures into a safe ``ObjectStorageError``."""
    try:
        yield
    except (BotoCoreError, ClientError, S3UploadFailedError, OSError) as err:
        raise ObjectStorageError(f"Object storage operation failed: {operation}") from err


class S3ObjectStorage:
    def __init__(self, client: Any, *, bucket: str, transfer: TransferConfig) -> None:
        self._client = client
        self._bucket = bucket
        self._transfer = transfer

    def put(
        self,
        scope: OwnerScope,
        key: str,
        data: BinaryIO,
        *,
        content_type: str,
        size_bytes: int,
        sha256: str,
    ) -> StoredObject:
        require_key_in_scope(scope, key)
        require_sha256(sha256)
        reader = _VerifyingReader(data)
        with _storage_errors("put object"):
            self._client.upload_fileobj(
                reader,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type, "Metadata": {CHECKSUM_METADATA: sha256}},
                Config=self._transfer,
            )
        stored_size = self._stored_size(key)
        if reader.size != size_bytes or reader.sha256 != sha256 or stored_size != size_bytes:
            with _storage_errors("delete mismatched object"):
                self._client.delete_object(Bucket=self._bucket, Key=key)
            raise ObjectIntegrityError("stored content does not match its size and checksum")
        return StoredObject(
            key=key, size_bytes=size_bytes, sha256=sha256, content_type=content_type
        )

    def get(self, scope: OwnerScope, key: str) -> bytes:
        require_key_in_scope(scope, key)
        try:
            with _storage_errors("get object"):
                response = self._client.get_object(Bucket=self._bucket, Key=key)
                content: bytes = response["Body"].read()
        except ObjectStorageError as err:
            if isinstance(err.__cause__, ClientError) and _is_not_found(err.__cause__):
                raise RecordNotFoundError("object not found") from None
            raise
        expected = response.get("Metadata", {}).get(CHECKSUM_METADATA)
        if expected is None or hashlib.sha256(content).hexdigest() != expected:
            raise ObjectIntegrityError("stored content does not match its recorded checksum")
        return content

    def head(self, scope: OwnerScope, key: str) -> StoredObject | None:
        require_key_in_scope(scope, key)
        response = self._head(key)
        if response is None:
            return None
        checksum = response.get("Metadata", {}).get(CHECKSUM_METADATA)
        if checksum is None:
            raise ObjectIntegrityError("object has no recorded checksum")
        return StoredObject(
            key=key,
            size_bytes=int(response["ContentLength"]),
            sha256=checksum,
            content_type=response.get("ContentType") or "application/octet-stream",
        )

    def delete(self, scope: OwnerScope, key: str) -> None:
        require_key_in_scope(scope, key)
        with _storage_errors("delete object"):
            self._client.delete_object(Bucket=self._bucket, Key=key)

    def abort_incomplete_uploads(self, *, initiated_before: datetime) -> int:
        aborted = 0
        with _storage_errors("abort incomplete uploads"):
            paginator = self._client.get_paginator("list_multipart_uploads")
            for page in paginator.paginate(Bucket=self._bucket):
                for upload in page.get("Uploads", []):
                    if upload["Initiated"] < initiated_before:
                        self._client.abort_multipart_upload(
                            Bucket=self._bucket, Key=upload["Key"], UploadId=upload["UploadId"]
                        )
                        aborted += 1
        return aborted

    def _head(self, key: str) -> dict[str, Any] | None:
        try:
            with _storage_errors("head object"):
                response: dict[str, Any] = self._client.head_object(Bucket=self._bucket, Key=key)
        except ObjectStorageError as err:
            if isinstance(err.__cause__, ClientError) and _is_not_found(err.__cause__):
                return None
            raise
        return response

    def _stored_size(self, key: str) -> int | None:
        response = self._head(key)
        return None if response is None else int(response["ContentLength"])


def create_s3_object_storage(settings: ObjectStorageSettings) -> S3ObjectStorage:
    """Build the adapter from validated settings. No network call is made here."""
    client = boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key.get_secret_value(),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=settings.connect_timeout_seconds,
            read_timeout=settings.read_timeout_seconds,
            retries={"max_attempts": settings.max_attempts, "mode": "standard"},
            # Send and check checksums only where S3 requires them: S3-compatible
            # stores differ in support for the newer default checksums. Integrity is
            # enforced by the SHA-256 check above instead.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
    transfer = TransferConfig(
        multipart_threshold=settings.multipart_threshold_bytes,
        multipart_chunksize=settings.multipart_chunk_bytes,
        use_threads=False,
    )
    return S3ObjectStorage(client, bucket=settings.bucket, transfer=transfer)
