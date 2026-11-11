"""Phase 8.3 step 1: the object-storage port, key rules and the in-memory fake.

No network: the S3 adapter is only checked for refusing a foreign key before
touching its client.
"""

import hashlib
import io
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.domain.errors import DomainValidationError, OwnershipError
from memory_engine.domain.identifiers import OwnerScope
from memory_engine.domain.object_storage import (
    ObjectStorage,
    StoredObject,
    owner_of_key,
    require_key_in_scope,
    validate_key,
)
from memory_engine.exceptions import ObjectIntegrityError, ObjectStorageError, RecordNotFoundError
from memory_engine.infrastructure.object_storage import InMemoryObjectStorage, S3ObjectStorage

OWNER = OwnerScope(uuid.UUID("00000000-0000-4000-8000-000000000001"))
OTHER = OwnerScope(uuid.UUID("00000000-0000-4000-8000-000000000002"))
KEY = f"documents/{OWNER.owner_id}/{uuid.uuid4()}/{uuid.uuid4()}/original"
CONTENT = b"Synthetic document content."
SHA = hashlib.sha256(CONTENT).hexdigest()


def _put(storage: ObjectStorage, scope: OwnerScope = OWNER, **overrides: Any) -> StoredObject:
    values: dict[str, Any] = {
        "content_type": "text/plain",
        "size_bytes": len(CONTENT),
        "sha256": SHA,
    }
    return storage.put(scope, overrides.pop("key", KEY), io.BytesIO(CONTENT), **values | overrides)


# --- keys ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        KEY,
        f"memory-sources/{OWNER.owner_id}/{uuid.uuid4()}",
        f"documents/{OWNER.owner_id}/a.b_c-1/original",
    ],
)
def test_owner_partitioned_keys_are_accepted(key: str) -> None:
    validate_key(key)
    assert owner_of_key(key) == OWNER.owner_id


@pytest.mark.parametrize(
    "key",
    [
        "",
        "documents",
        f"/documents/{OWNER.owner_id}/x",
        f"documents/{OWNER.owner_id}/../x",
        f"documents/{OWNER.owner_id}//x",
        f"documents/{OWNER.owner_id}/x/",
        f"Documents/{OWNER.owner_id}/x",
        f"documents/{OWNER.owner_id}/.hidden",
        f"documents/{OWNER.owner_id}/report final.pdf",
        "documents/not-a-uuid/x",
        f"documents/{OWNER.owner_id}/" + "a" * 600,
    ],
)
def test_unsafe_or_ownerless_keys_are_rejected(key: str) -> None:
    with pytest.raises(DomainValidationError):
        validate_key(key)


def test_a_key_of_another_owner_is_refused() -> None:
    require_key_in_scope(OWNER, KEY)
    with pytest.raises(OwnershipError):
        require_key_in_scope(OTHER, KEY)


def test_stored_object_metadata_is_validated() -> None:
    assert (
        StoredObject(key=KEY, size_bytes=0, sha256=SHA, content_type="text/plain").size_bytes == 0
    )
    for overrides in ({"size_bytes": -1}, {"sha256": "ABC"}, {"content_type": " "}, {"key": "x"}):
        values: dict[str, Any] = {
            "key": KEY,
            "size_bytes": 1,
            "sha256": SHA,
            "content_type": "text/plain",
        }
        with pytest.raises(DomainValidationError):
            StoredObject(**values | overrides)


# --- in-memory fake ------------------------------------------------------------------


def test_fake_round_trip_and_idempotent_delete() -> None:
    storage = InMemoryObjectStorage()
    stored = _put(storage)
    assert stored == StoredObject(
        key=KEY, size_bytes=len(CONTENT), sha256=SHA, content_type="text/plain"
    )
    assert storage.get(OWNER, KEY) == CONTENT
    assert storage.head(OWNER, KEY) == stored
    storage.delete(OWNER, KEY)
    storage.delete(OWNER, KEY)
    assert storage.head(OWNER, KEY) is None
    with pytest.raises(RecordNotFoundError):
        storage.get(OWNER, KEY)


@pytest.mark.parametrize(
    "overrides",
    [{"size_bytes": len(CONTENT) + 1}, {"sha256": hashlib.sha256(b"other").hexdigest()}],
)
def test_fake_stores_nothing_when_size_or_checksum_disagree(overrides: dict[str, Any]) -> None:
    storage = InMemoryObjectStorage()
    with pytest.raises(ObjectIntegrityError):
        _put(storage, **overrides)
    assert storage.head(OWNER, KEY) is None


def test_fake_checks_ownership_before_anything_else() -> None:
    storage = InMemoryObjectStorage()
    storage.available = False
    with pytest.raises(OwnershipError):
        _put(storage, scope=OTHER)
    for call in (storage.get, storage.head, storage.delete):
        with pytest.raises(OwnershipError):
            call(OTHER, KEY)


def test_fake_reports_an_outage() -> None:
    storage = InMemoryObjectStorage()
    _put(storage)
    storage.available = False
    with pytest.raises(ObjectStorageError):
        _put(storage)
    with pytest.raises(ObjectStorageError):
        storage.get(OWNER, KEY)
    with pytest.raises(ObjectStorageError):
        storage.abort_incomplete_uploads(initiated_before=datetime.now(UTC))
    storage.available = True
    assert storage.abort_incomplete_uploads(initiated_before=datetime.now(UTC)) == 0


def test_fake_rejects_a_malformed_checksum_argument() -> None:
    with pytest.raises(DomainValidationError):
        _put(InMemoryObjectStorage(), sha256="not-a-sha")


# --- S3 adapter, no network ----------------------------------------------------------


class _NoCallsClient:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the client must not be used: {name}")


def test_s3_adapter_refuses_a_foreign_key_before_using_its_client() -> None:
    storage = S3ObjectStorage(_NoCallsClient(), bucket="raven-memory", transfer=None)
    with pytest.raises(OwnershipError):
        _put(storage, scope=OTHER)
    for call in (storage.get, storage.head, storage.delete):
        with pytest.raises(OwnershipError):
            call(OTHER, KEY)


def test_both_adapters_satisfy_the_port() -> None:
    adapters: list[ObjectStorage] = [
        InMemoryObjectStorage(),
        S3ObjectStorage(_NoCallsClient(), bucket="raven-memory", transfer=None),
    ]
    assert len(adapters) == 2
