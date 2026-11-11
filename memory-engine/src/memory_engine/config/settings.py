"""Memory Engine settings.

Configuration comes from environment variables prefixed ``RAVEN_MEMORY__``
(nested values use ``__``), and optionally from an explicitly named ``.env``
file. No ``.env`` file is read unless one is passed to :func:`load_settings`.

Secrets use :class:`pydantic.SecretStr` so they are masked in ``repr`` and
``str``. The database connection itself is built in
``memory_engine.infrastructure.persistence`` (Phase 8.2, psycopg 3 with
synchronous SQLAlchemy); the object-storage client in
``memory_engine.infrastructure.object_storage`` (Phase 8.3, boto3); the broker
connection and outbox relay in ``memory_engine.infrastructure.messaging``
(Phase 8.3 step 4, RabbitMQ through Celery).
"""

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from memory_engine.exceptions.base import ConfigurationError

ENV_PREFIX = "RAVEN_MEMORY__"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Environment(StrEnum):
    """The four logical environments (Phase 7.8 section 4)."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseModel):
    """PostgreSQL connection and pool settings (Phase 7.1 section 23.2).

    Pool defaults are starting values, to be tuned by measurement (7.2 section 9).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(min_length=1)
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: SecretStr
    # Logical schema owned by the Memory Engine (Phase 7.2).
    schema_name: str = Field(default="memory", pattern=r"^[a-z_][a-z0-9_]*$")
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=100)
    pool_recycle_seconds: int = Field(default=1800, ge=30)
    connect_timeout_seconds: int = Field(default=10, ge=1, le=300)

    @field_validator("password")
    @classmethod
    def _password_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("must not be empty")
        return value


MIB = 1024 * 1024


class ObjectStorageSettings(BaseModel):
    """S3-compatible object storage (7.1 sections 8 and 24.1).

    One bucket per engine; keys are owner-partitioned. The bucket is provisioned
    outside the application, which never creates buckets.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint_url: str = Field(pattern=r"^https?://[^\s/]+(/[^\s]*)?$")
    region: str = Field(default="us-east-1", min_length=1)
    # S3 bucket naming rules: 3-63 characters, lowercase letters, digits, dots, hyphens.
    bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    access_key_id: str = Field(min_length=1)
    secret_access_key: SecretStr
    # S3 parts must be at least 5 MiB, except the last.
    multipart_threshold_bytes: int = Field(default=8 * MIB, ge=5 * MIB)
    multipart_chunk_bytes: int = Field(default=8 * MIB, ge=5 * MIB)
    connect_timeout_seconds: int = Field(default=5, ge=1, le=120)
    read_timeout_seconds: int = Field(default=30, ge=1, le=600)
    max_attempts: int = Field(default=3, ge=1, le=10)

    @field_validator("secret_access_key")
    @classmethod
    def _secret_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("must not be empty")
        return value


class IngestionSettings(BaseModel):
    """Input size limits (plan 8.3 section 5.1). Owner-approved defaults, 2026-11-11.

    The values are configurable because 7.6 section 18 defers the final limits.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_text_bytes: int = Field(default=256 * 1024, ge=1, le=16 * MIB)
    max_conversation_messages: int = Field(default=1000, ge=1, le=100_000)
    max_conversation_bytes: int = Field(default=4 * MIB, ge=1, le=64 * MIB)
    # Document uploads (8.3 step 3): checked and hashed in memory up to this size.
    max_upload_bytes: int = Field(default=25 * MIB, ge=1, le=512 * MIB)


class BrokerSettings(BaseModel):
    """RabbitMQ connection for handoff messages (7.4; 7.1 section 24.3).

    ``use_tls`` must be enabled outside development and testing (7.4 section 18);
    the local test broker listens on 127.0.0.1 without TLS.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(min_length=1)
    port: int = Field(default=5672, ge=1, le=65535)
    virtual_host: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    user: str = Field(min_length=1)
    password: SecretStr
    use_tls: bool = False
    connect_timeout_seconds: int = Field(default=5, ge=1, le=120)
    # How long to wait for the broker to confirm one message (publisher confirms).
    confirm_timeout_seconds: int = Field(default=10, ge=1, le=300)

    @field_validator("password")
    @classmethod
    def _password_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("must not be empty")
        return value


class OutboxSettings(BaseModel):
    """Outbox relay policy (owner-approved defaults, 8.3 step 4).

    7.4 section 22 defers retry counts and delays, so these are configurable:
    exponential backoff from ``backoff_base_seconds`` doubling up to
    ``backoff_max_seconds``, with jitter; after ``max_attempts`` failures a
    message becomes ``failed`` until an explicit retry.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    batch_size: int = Field(default=100, ge=1, le=10_000)
    max_attempts: int = Field(default=10, ge=1, le=1000)
    backoff_base_seconds: float = Field(default=2.0, gt=0, le=3600)
    backoff_max_seconds: float = Field(default=300.0, gt=0, le=86_400)
    poll_interval_seconds: float = Field(default=2.0, gt=0, le=3600)


class MemoryEngineSettings(BaseSettings):
    """Top-level Memory Engine configuration."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        frozen=True,
        env_file=None,
    )

    environment: Environment
    app_name: str = Field(default="raven-memory-engine", min_length=1)
    log_level: LogLevel = "INFO"
    database: DatabaseSettings
    object_storage: ObjectStorageSettings
    broker: BrokerSettings
    ingestion: IngestionSettings = IngestionSettings()
    outbox: OutboxSettings = OutboxSettings()


def load_settings(env_file: str | Path | None = None) -> MemoryEngineSettings:
    """Load and validate settings, failing clearly on missing or invalid values.

    Args:
        env_file: Optional ``.env`` file to read in addition to the process
            environment. Environment variables take precedence. Nothing is read
            from disk when this is ``None``.

    Raises:
        ConfigurationError: If configuration is missing or invalid. The error
            lists the offending fields and problem types only. The original
            :class:`pydantic.ValidationError` is deliberately not chained,
            because it embeds raw input values that can include secrets.
    """
    if env_file is not None and not Path(env_file).is_file():
        raise ConfigurationError(f"Configuration file not found: {Path(env_file).name}")
    try:
        return MemoryEngineSettings(_env_file=env_file)
    except ValidationError as err:
        problems = {
            ".".join(str(part) for part in error["loc"]) or "<root>": error["type"]
            for error in err.errors(include_url=False, include_input=False, include_context=False)
        }
        summary = ", ".join(f"{field} ({kind})" for field, kind in sorted(problems.items()))
        raise ConfigurationError(
            f"Invalid Memory Engine configuration: {summary}", details=problems
        ) from None
