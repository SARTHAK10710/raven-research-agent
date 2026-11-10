"""Memory Engine settings.

Configuration comes from environment variables prefixed ``RAVEN_MEMORY__``
(nested values use ``__``), and optionally from an explicitly named ``.env``
file. No ``.env`` file is read unless one is passed to :func:`load_settings`.

Secrets use :class:`pydantic.SecretStr` so they are masked in ``repr`` and
``str``. Phase 8.1 validates database settings but does not connect to a
database; the driver and connection code arrive in Phase 8.2.
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
    """PostgreSQL connection settings. Validated only; no connection in Phase 8.1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(min_length=1)
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(min_length=1)
    user: str = Field(min_length=1)
    password: SecretStr
    # Logical schema owned by the Memory Engine (Phase 7.2).
    schema_name: str = Field(default="memory", pattern=r"^[a-z_][a-z0-9_]*$")

    @field_validator("password")
    @classmethod
    def _password_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("must not be empty")
        return value


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
