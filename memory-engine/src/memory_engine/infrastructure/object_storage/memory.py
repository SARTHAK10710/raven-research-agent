"""In-memory object storage for unit tests (7.1 section 24.1).

Implements the same contract as the S3 adapter: owner checks before access,
size and checksum verification before anything is stored, idempotent delete.
``available = False`` simulates an outage.
"""

import hashlib
from datetime import datetime
from typing import BinaryIO

from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.object_storage import (
    StoredObject,
    require_key_in_scope,
    require_sha256,
)
from memory_engine.exceptions import ObjectIntegrityError, ObjectStorageError, RecordNotFoundError


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.available = True
        self._objects: dict[str, tuple[StoredObject, bytes]] = {}

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
        self._require_available()
        content = data.read()
        if len(content) != size_bytes or hashlib.sha256(content).hexdigest() != sha256:
            raise ObjectIntegrityError("stored content does not match its size and checksum")
        stored = StoredObject(
            key=key, size_bytes=size_bytes, sha256=sha256, content_type=content_type
        )
        self._objects[key] = (stored, content)
        return stored

    def get(self, scope: OwnerScope, key: str) -> bytes:
        require_key_in_scope(scope, key)
        self._require_available()
        if key not in self._objects:
            raise RecordNotFoundError("object not found")
        return self._objects[key][1]

    def head(self, scope: OwnerScope, key: str) -> StoredObject | None:
        require_key_in_scope(scope, key)
        self._require_available()
        entry = self._objects.get(key)
        return None if entry is None else entry[0]

    def delete(self, scope: OwnerScope, key: str) -> None:
        require_key_in_scope(scope, key)
        self._require_available()
        self._objects.pop(key, None)

    def abort_incomplete_uploads(self, *, initiated_before: datetime) -> int:
        self._require_available()
        return 0  # uploads here are never partial

    def _require_available(self) -> None:
        if not self.available:
            raise ObjectStorageError("object storage is unavailable")
