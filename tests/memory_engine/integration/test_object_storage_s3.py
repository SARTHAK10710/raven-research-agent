"""Phase 8.3 step 1: the S3 adapter against SeaweedFS (real S3 API).

Start the store with ``docker compose up -d --wait object-storage-test``. Tests
skip with a message when it is unreachable. Each test module uses a throwaway
bucket, removed afterwards. Also covers the object-storage failure tests that
8.2 deferred to 8.3 (store unavailable, partial upload).
"""

import hashlib
import io
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, BinaryIO, cast

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import SecretStr

from memory_engine.config import ObjectStorageSettings
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.exceptions import ObjectIntegrityError, ObjectStorageError, RecordNotFoundError
from memory_engine.infrastructure.object_storage import S3ObjectStorage, create_s3_object_storage

pytestmark = pytest.mark.integration

MIB = 1024 * 1024
ENDPOINT = os.environ.get("RAVEN_TEST_OBJECT_STORAGE_URL", "http://127.0.0.1:58333")
ACCESS_KEY = "raven_test_access"
SECRET_KEY = "raven_test_only_secret"  # noqa: S105 - test-only value from docker/seaweedfs/s3.json


def _settings(bucket: str, **overrides: Any) -> ObjectStorageSettings:
    values: dict[str, Any] = {
        "endpoint_url": ENDPOINT,
        "bucket": bucket,
        "access_key_id": ACCESS_KEY,
        "secret_access_key": SecretStr(SECRET_KEY),
        "multipart_threshold_bytes": 5 * MIB,
        "multipart_chunk_bytes": 5 * MIB,
        "connect_timeout_seconds": 2,
        "read_timeout_seconds": 10,
        "max_attempts": 1,
    }
    return ObjectStorageSettings(**values | overrides)


@pytest.fixture(scope="module")
def raw_client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=2,
            retries={"max_attempts": 1},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


@pytest.fixture(scope="module")
def bucket(raw_client: Any) -> Iterator[str]:
    name = f"raven-test-{uuid.uuid4().hex[:12]}"
    try:
        raw_client.create_bucket(Bucket=name)
    except (BotoCoreError, ClientError):
        pytest.skip(
            "Object storage unreachable; run `docker compose up -d --wait object-storage-test`"
        )
    yield name
    for upload in raw_client.list_multipart_uploads(Bucket=name).get("Uploads", []):
        raw_client.abort_multipart_upload(
            Bucket=name, Key=upload["Key"], UploadId=upload["UploadId"]
        )
    for item in raw_client.list_objects_v2(Bucket=name).get("Contents", []):
        raw_client.delete_object(Bucket=name, Key=item["Key"])
    raw_client.delete_bucket(Bucket=name)


@pytest.fixture
def storage(bucket: str) -> S3ObjectStorage:
    return create_s3_object_storage(_settings(bucket))


@pytest.fixture
def owner() -> OwnerScope:
    return OwnerScope(uuid.uuid4())


def _key(owner: OwnerScope) -> str:
    return f"documents/{owner.owner_id}/{uuid.uuid4()}/{uuid.uuid4()}/original"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _uploads(raw_client: Any, bucket: str, key: str) -> list[Any]:
    uploads = raw_client.list_multipart_uploads(Bucket=bucket).get("Uploads", [])
    return [u for u in uploads if u["Key"] == key]


def test_round_trip_keeps_size_type_and_checksum(
    storage: S3ObjectStorage, owner: OwnerScope
) -> None:
    key, data = _key(owner), b"Synthetic document content."
    stored = storage.put(
        owner,
        key,
        io.BytesIO(data),
        content_type="text/plain",
        size_bytes=len(data),
        sha256=_sha(data),
    )
    assert storage.head(owner, key) == stored
    assert stored.size_bytes == len(data) and stored.content_type == "text/plain"
    assert storage.get(owner, key) == data
    storage.delete(owner, key)
    storage.delete(owner, key)  # idempotent
    assert storage.head(owner, key) is None
    with pytest.raises(RecordNotFoundError):
        storage.get(owner, key)


def test_large_content_is_uploaded_in_parts(
    storage: S3ObjectStorage, owner: OwnerScope, raw_client: Any, bucket: str
) -> None:
    key, data = _key(owner), os.urandom(11 * MIB)  # three parts at 5 MiB
    stored = storage.put(
        owner,
        key,
        io.BytesIO(data),
        content_type="application/pdf",
        size_bytes=len(data),
        sha256=_sha(data),
    )
    assert stored.size_bytes == len(data)
    assert storage.get(owner, key) == data
    assert _uploads(raw_client, bucket, key) == []


@pytest.mark.parametrize("mismatch", ["checksum", "size"])
def test_a_mismatched_upload_leaves_no_object(
    storage: S3ObjectStorage, owner: OwnerScope, mismatch: str
) -> None:
    key, data = _key(owner), b"Synthetic content."
    sha = _sha(b"something else") if mismatch == "checksum" else _sha(data)
    size = len(data) + (1 if mismatch == "size" else 0)
    with pytest.raises(ObjectIntegrityError):
        storage.put(
            owner, key, io.BytesIO(data), content_type="text/plain", size_bytes=size, sha256=sha
        )
    assert storage.head(owner, key) is None


def test_content_corrupted_in_the_store_is_detected_on_read(
    storage: S3ObjectStorage, owner: OwnerScope, raw_client: Any, bucket: str
) -> None:
    key, data = _key(owner), b"Original synthetic content."
    storage.put(
        owner,
        key,
        io.BytesIO(data),
        content_type="text/plain",
        size_bytes=len(data),
        sha256=_sha(data),
    )
    raw_client.put_object(
        Bucket=bucket, Key=key, Body=b"Tampered content!!!!!!!!!!!", Metadata={"sha256": _sha(data)}
    )
    with pytest.raises(ObjectIntegrityError):
        storage.get(owner, key)


class _BrokenStream:
    """Delivers ``good`` bytes, then fails as a dropped client connection would."""

    def __init__(self, good: int) -> None:
        self._left = good

    def read(self, size: int = -1) -> bytes:
        if self._left <= 0:
            raise OSError("connection reset by peer")
        n = self._left if size < 0 else min(size, self._left)
        self._left -= n
        return b"x" * n


def test_an_interrupted_multipart_upload_leaves_nothing_behind(
    storage: S3ObjectStorage, owner: OwnerScope, raw_client: Any, bucket: str
) -> None:
    key = _key(owner)
    with pytest.raises(ObjectStorageError):
        storage.put(
            owner,
            key,
            cast(BinaryIO, _BrokenStream(good=6 * MIB)),  # fails during the second part
            content_type="application/pdf",
            size_bytes=12 * MIB,
            sha256="0" * 64,
        )
    assert storage.head(owner, key) is None
    assert _uploads(raw_client, bucket, key) == []


def test_incomplete_uploads_from_a_crash_are_cleaned_up(
    storage: S3ObjectStorage, owner: OwnerScope, raw_client: Any, bucket: str
) -> None:
    key = _key(owner)
    raw_client.create_multipart_upload(Bucket=bucket, Key=key)  # never completed
    assert (
        storage.abort_incomplete_uploads(initiated_before=datetime.now(UTC) - timedelta(hours=1))
        == 0
    )
    assert len(_uploads(raw_client, bucket, key)) == 1
    aborted = storage.abort_incomplete_uploads(
        initiated_before=datetime.now(UTC) + timedelta(minutes=5)
    )
    assert aborted >= 1
    assert _uploads(raw_client, bucket, key) == []


def test_an_unreachable_store_raises_a_storage_error(owner: OwnerScope) -> None:
    # A closed local port: the failure must be reported, never treated as stored.
    storage = create_s3_object_storage(
        _settings("raven-unreachable", endpoint_url="http://127.0.0.1:1", connect_timeout_seconds=1)
    )
    data = b"content"
    with pytest.raises(ObjectStorageError) as caught:
        storage.put(
            owner,
            _key(owner),
            io.BytesIO(data),
            content_type="text/plain",
            size_bytes=len(data),
            sha256=_sha(data),
        )
    assert "content" not in str(caught.value)
    with pytest.raises(ObjectStorageError):
        storage.head(owner, _key(owner))
