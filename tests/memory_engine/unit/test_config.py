"""Plan 8.1 initial tests 2-4: configuration validation, missing and invalid values."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from memory_engine.config import ENV_PREFIX, Environment, load_settings
from memory_engine.exceptions import ConfigurationError


def _write_env_file(path: Path, values: dict[str, str]) -> Path:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), "utf-8")
    return path


# --- valid configuration ---------------------------------------------------


def test_valid_configuration_loads(valid_env: dict[str, str]) -> None:
    settings = load_settings()

    assert settings.environment is Environment.TESTING
    assert settings.app_name == "raven-memory-engine"
    assert settings.log_level == "INFO"
    assert settings.database.host == "db.test.invalid"
    assert settings.database.port == 5432
    assert settings.database.schema_name == "memory"


def test_optional_values_can_be_overridden(
    valid_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(f"{ENV_PREFIX}DATABASE__PORT", "6543")

    settings = load_settings()

    assert settings.log_level == "DEBUG"
    assert settings.database.port == 6543


def test_settings_are_immutable(valid_env: dict[str, str]) -> None:
    settings = load_settings()
    with pytest.raises(ValidationError):
        settings.log_level = "DEBUG"  # type: ignore[misc]


# --- missing mandatory configuration ------------------------------------------


def test_missing_configuration_fails_clearly() -> None:
    with pytest.raises(ConfigurationError) as caught:
        load_settings()

    assert caught.value.details == {"database": "missing", "environment": "missing"}
    assert "environment (missing)" in caught.value.message


def test_missing_nested_value_names_the_field(
    valid_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(f"{ENV_PREFIX}DATABASE__NAME")

    with pytest.raises(ConfigurationError) as caught:
        load_settings()

    assert caught.value.details == {"database.name": "missing"}


# --- invalid values ----------------------------------------------------------


@pytest.mark.parametrize(
    ("variable", "value", "field"),
    [
        ("ENVIRONMENT", "prod", "environment"),
        ("LOG_LEVEL", "VERBOSE", "log_level"),
        ("APP_NAME", "", "app_name"),
        ("DATABASE__PORT", "70000", "database.port"),
        ("DATABASE__PORT", "0", "database.port"),
        ("DATABASE__PORT", "not-a-port", "database.port"),
        ("DATABASE__HOST", "", "database.host"),
        ("DATABASE__PASSWORD", "", "database.password"),
        ("DATABASE__SCHEMA_NAME", "memory; DROP SCHEMA", "database.schema_name"),
    ],
)
def test_invalid_values_are_rejected(
    valid_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
    field: str,
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}{variable}", value)

    with pytest.raises(ConfigurationError) as caught:
        load_settings()

    assert field in caught.value.details


# --- secrets ----------------------------------------------------------------


def test_password_is_masked_in_settings(valid_env: dict[str, str], synthetic_password: str) -> None:
    settings = load_settings()

    assert synthetic_password not in repr(settings)
    assert synthetic_password not in str(settings.database)
    assert settings.database.password.get_secret_value() == synthetic_password


def test_configuration_errors_never_expose_secrets(
    valid_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, synthetic_password: str
) -> None:
    # A missing nested field makes pydantic report the whole database mapping,
    # including the password, as the offending input.
    monkeypatch.delenv(f"{ENV_PREFIX}DATABASE__HOST")

    with pytest.raises(ConfigurationError) as caught:
        load_settings()

    error = caught.value
    exposed = f"{error} {error!r} {error.details!r} {error.args!r}"
    assert synthetic_password not in exposed
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


# --- .env handling ------------------------------------------------------------


def test_env_file_in_working_directory_is_not_read_implicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid_env: dict[str, str]
) -> None:
    _write_env_file(tmp_path / ".env", valid_env)
    for key in valid_env:
        monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError):
        load_settings()


def test_explicit_env_file_is_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid_env: dict[str, str]
) -> None:
    env_file = _write_env_file(tmp_path / "memory.env", valid_env)
    for key in valid_env:
        monkeypatch.delenv(key)

    settings = load_settings(env_file)

    assert settings.database.name == "raven_test"


def test_environment_variables_override_env_file(tmp_path: Path, valid_env: dict[str, str]) -> None:
    env_file = _write_env_file(
        tmp_path / "memory.env", {**valid_env, f"{ENV_PREFIX}ENVIRONMENT": "staging"}
    )

    assert load_settings(env_file).environment is Environment.TESTING


def test_unknown_prefixed_key_in_env_file_is_rejected(
    tmp_path: Path, valid_env: dict[str, str]
) -> None:
    env_file = _write_env_file(tmp_path / "memory.env", {f"{ENV_PREFIX}UNKNOWN_SETTING": "x"})

    with pytest.raises(ConfigurationError):
        load_settings(env_file)


def test_missing_env_file_fails_clearly(tmp_path: Path, valid_env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(tmp_path / "absent.env")
