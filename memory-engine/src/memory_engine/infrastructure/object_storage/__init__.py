"""Adapters for the shared object-storage port (``memory_engine.domain.object_storage``).

* :class:`InMemoryObjectStorage`: a fake for unit tests (7.1 section 24.1).
* :class:`S3ObjectStorage`: boto3 against any S3-compatible endpoint; SeaweedFS
  in development and integration tests.
"""

from memory_engine.infrastructure.object_storage.memory import InMemoryObjectStorage
from memory_engine.infrastructure.object_storage.s3 import (
    S3ObjectStorage,
    create_s3_object_storage,
)

__all__ = ["InMemoryObjectStorage", "S3ObjectStorage", "create_s3_object_storage"]
