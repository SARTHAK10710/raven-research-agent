"""Object-storage port shared by Personal Memory and Document Intelligence.

Approved in 7.1 section 24.1 (Decision 8): application code depends only on
this port; the S3-compatible adapter and an in-memory fake live in
``memory_engine.infrastructure.object_storage``.

Keys are opaque and owner-partitioned (7.2 section 10): ``<area>/<owner_id>/...``,
for example ``documents/{owner}/{document}/{version}/original``. Every call
names the caller's :class:`OwnerScope`, and a key whose owner segment differs
is refused before any storage access, so one owner can never read, overwrite
or delete another owner's object even through a wrongly built key.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Protocol

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope

# Lowercase area prefix, then segments that start with a letter or digit, so
# "", "." and ".." can never appear as a segment (no path traversal).
_KEY_PATTERN = re.compile(r"[a-z][a-z0-9-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)+")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
MAX_KEY_LENGTH = 512


def validate_key(key: str) -> None:
    """Reject keys that are not opaque, owner-partitioned paths."""
    if len(key) > MAX_KEY_LENGTH or not _KEY_PATTERN.fullmatch(key):
        raise DomainValidationError("object key is not a valid owner-partitioned key")
    owner_of_key(key)


def owner_of_key(key: str) -> uuid.UUID:
    """The owner identifier encoded in the key's second segment."""
    parts = key.split("/")
    try:
        return uuid.UUID(parts[1])
    except (IndexError, ValueError) as err:
        raise DomainValidationError("object key does not name an owner") from err


def require_key_in_scope(scope: OwnerScope, key: str) -> None:
    validate_key(key)
    if not scope.owns(owner_of_key(key)):
        raise OwnershipError("object key belongs to a different owner scope")


def require_sha256(value: str) -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise DomainValidationError("sha256 must be 64 lowercase hex characters")


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredObject:
    """What object storage holds under a key. Never the content itself."""

    key: str
    size_bytes: int
    sha256: str
    content_type: str

    def __post_init__(self) -> None:
        validate_key(self.key)
        if self.size_bytes < 0:
            raise DomainValidationError("size_bytes must not be negative")
        require_sha256(self.sha256)
        if not self.content_type.strip():
            raise DomainValidationError("content_type must not be empty")


class ObjectStorage(Protocol):
    """Owner-scoped access to large content (7.1 section 8; 7.2 sections 10-11).

    Errors: :class:`~memory_engine.exceptions.ObjectStorageError` when the store
    fails or is unreachable; :class:`~memory_engine.exceptions.ObjectIntegrityError`
    when stored bytes would not match ``size_bytes`` and ``sha256`` (nothing is
    left stored); :class:`OwnershipError` for a key outside ``scope``.
    """

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
        """Store ``data`` under ``key``, verifying the size and checksum the caller
        computed beforehand (plan 8.3 section 6.1 computes the checksum before storing).

        Large content is uploaded in parts; a failed upload is aborted, so no
        partial object becomes visible.
        """
        ...

    def get(self, scope: OwnerScope, key: str) -> bytes:
        """The object's content. A missing object raises ``RecordNotFoundError``."""
        ...

    def head(self, scope: OwnerScope, key: str) -> StoredObject | None:
        """The object's metadata, or ``None`` when no object exists under ``key``."""
        ...

    def delete(self, scope: OwnerScope, key: str) -> None:
        """Remove the object. Idempotent: deleting a missing object succeeds."""
        ...

    def abort_incomplete_uploads(self, *, initiated_before: datetime) -> int:
        """Maintenance: abort multipart uploads started before ``initiated_before``
        that never completed (for example after a worker crash; 7.2 section 11).
        Returns how many were aborted.
        """
        ...
