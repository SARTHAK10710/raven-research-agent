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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
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


class ExtractionSettings(BaseModel):
    """Extraction worker policy (owner-approved, 8.4 step 1; 7.1 section 25).

    Retries cover transient failures (database, object storage) through Celery,
    with exponential backoff; when they run out, the source becomes
    ``processing_failed``. The language thresholds drive the deterministic
    English check (G6); they are uncalibrated defaults, checked against the
    synthetic dataset.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_retries: int = Field(default=5, ge=0, le=100)
    retry_backoff_seconds: float = Field(default=2.0, gt=0, le=3600)
    retry_backoff_max_seconds: float = Field(default=300.0, gt=0, le=86_400)
    # Texts with fewer words are treated as English unless mostly non-Latin.
    language_min_words: int = Field(default=6, ge=1, le=1000)
    # Defer when fewer than this share of the words are common English words.
    english_min_function_word_share: float = Field(default=0.2, ge=0, le=1)
    # Defer when more than this share of the letters are not Latin script.
    max_non_latin_letter_share: float = Field(default=0.3, ge=0, le=1)


class RelevanceSettings(BaseModel):
    """Relevance gate scoring (owner-approved, 8.4 step 2; 6.2.2 section 4.5).

    Uncalibrated defaults: 6.2.2 leaves weights and thresholds to evaluation
    data. A signal that cannot be evaluated is left out and the remaining
    weights are renormalized; it is never counted as zero (6.2.2 AC-07).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    weight_personal: float = Field(default=0.35, ge=0, le=1)
    weight_utility: float = Field(default=0.2, ge=0, le=1)
    weight_temporal: float = Field(default=0.15, ge=0, le=1)
    weight_context: float = Field(default=0.15, ge=0, le=1)
    weight_density: float = Field(default=0.15, ge=0, le=1)
    process_threshold: float = Field(default=0.5, ge=0, le=1)
    defer_threshold: float = Field(default=0.3, ge=0, le=1)

    @model_validator(mode="after")
    def _ordered(self) -> "RelevanceSettings":
        if self.defer_threshold > self.process_threshold:
            raise ValueError("defer_threshold must not exceed process_threshold")
        weights = (
            self.weight_personal,
            self.weight_utility,
            self.weight_temporal,
            self.weight_context,
            self.weight_density,
        )
        if sum(weights) <= 0:
            raise ValueError("at least one weight must be positive")
        return self


class FactExtractionSettings(BaseModel):
    """Extraction confidence (owner-approved, 8.4 step 3; 6.2.3 section 5.9).

    A deductive score: 1.0 minus a penalty per weakness. Below
    ``review_threshold`` a proposal needs review; below ``reject_threshold`` it
    is rejected. Uncalibrated defaults; extraction confidence is never fact
    confidence (6.2.3 AC-16).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    penalty_no_subject: float = Field(default=0.4, ge=0, le=1)
    penalty_no_verb: float = Field(default=0.4, ge=0, le=1)
    penalty_unresolved_reference: float = Field(default=0.3, ge=0, le=1)
    penalty_no_object: float = Field(default=0.2, ge=0, le=1)
    penalty_long_sentence: float = Field(default=0.1, ge=0, le=1)
    long_sentence_tokens: int = Field(default=30, ge=5, le=1000)
    review_threshold: float = Field(default=0.5, ge=0, le=1)
    reject_threshold: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def _ordered(self) -> "FactExtractionSettings":
        if self.reject_threshold > self.review_threshold:
            raise ValueError("reject_threshold must not exceed review_threshold")
        return self


class EvaluationSettings(BaseModel):
    """Evaluation rule tables (owner-approved, 8.4 step 4; 6.2.4).

    Importance by what a fact is about, fact confidence by its evidence
    situation; independent of each other and of extraction confidence.
    Uncalibrated defaults.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    importance_goal: float = Field(default=0.85, ge=0, le=1)
    importance_commitment: float = Field(default=0.85, ge=0, le=1)
    importance_decision: float = Field(default=0.85, ge=0, le=1)
    importance_relationship: float = Field(default=0.85, ge=0, le=1)
    importance_health_identity: float = Field(default=0.85, ge=0, le=1)
    importance_preference: float = Field(default=0.7, ge=0, le=1)
    importance_habit: float = Field(default=0.6, ge=0, le=1)
    importance_event: float = Field(default=0.4, ge=0, le=1)
    importance_other: float = Field(default=0.3, ge=0, le=1)
    remember_bonus: float = Field(default=0.1, ge=0, le=1)
    confidence_direct: float = Field(default=0.9, ge=0, le=1)
    confidence_intended: float = Field(default=0.8, ge=0, le=1)
    confidence_conditional: float = Field(default=0.6, ge=0, le=1)
    confidence_possible: float = Field(default=0.5, ge=0, le=1)
    confidence_reported: float = Field(default=0.35, ge=0, le=1)
    unresolved_penalty: float = Field(default=0.2, ge=0, le=1)
    # Outcome policy: review below this fact confidence; reject below this
    # importance unless the user asked to remember.
    review_fact_confidence: float = Field(default=0.4, ge=0, le=1)
    reject_importance: float = Field(default=0.2, ge=0, le=1)


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
    extraction: ExtractionSettings = ExtractionSettings()
    relevance: RelevanceSettings = RelevanceSettings()
    facts: FactExtractionSettings = FactExtractionSettings()
    evaluation: EvaluationSettings = EvaluationSettings()


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
