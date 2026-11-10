"""Plan 8.1 initial test 7: logging initialization, plus privacy behavior."""

import io
import json
import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from memory_engine.config import ENV_PREFIX, load_settings
from memory_engine.exceptions import PersistenceError
from memory_engine.observability import (
    LOGGER_NAMESPACE,
    REDACTED,
    configure_logging,
    get_logger,
    log_context,
)

REQUIRED_FIELDS = {"timestamp", "level", "service", "environment", "component", "message"}


def _configure(stream: io.StringIO) -> logging.Logger:
    return configure_logging(load_settings(), stream=stream)


def _records(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def test_logging_initializes_with_structured_fields(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)

    get_logger("ingestion").info(
        "Memory source registered",
        extra={"event_type": "source.registered", "operation": "register_source"},
    )

    [record] = _records(stream)
    assert record.keys() >= REQUIRED_FIELDS
    assert record["level"] == "INFO"
    assert record["service"] == "raven-memory-engine"
    assert record["environment"] == "testing"
    assert record["component"] == f"{LOGGER_NAMESPACE}.ingestion"
    assert record["message"] == "Memory source registered"
    assert record["event_type"] == "source.registered"
    assert record["operation"] == "register_source"
    assert datetime.fromisoformat(record["timestamp"]).tzinfo == UTC


def test_correlation_identifiers_are_included_and_scoped(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)
    logger = get_logger("retrieval")

    with log_context(request_id="req-1", execution_id="exec-1"):
        with log_context(task_id="task-1"):
            logger.info("inner")
        logger.info("outer")
    logger.info("after")

    inner, outer, after = _records(stream)
    assert (inner["request_id"], inner["execution_id"], inner["task_id"]) == (
        "req-1",
        "exec-1",
        "task-1",
    )
    assert "task_id" not in outer and outer["request_id"] == "req-1"
    assert "request_id" not in after


def test_context_is_restored_after_an_exception(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)

    with pytest.raises(RuntimeError), log_context(request_id="req-err"):
        raise RuntimeError("boom")
    get_logger("ingestion").info("after")

    assert "request_id" not in _records(stream)[0]


def test_unknown_correlation_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="user_email"), log_context(user_email="x"):
        pass


def test_sensitive_extra_fields_are_redacted(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)
    secrets = {"password": "pw-1", "api_key": "key-2", "database_dsn": "postgresql://u:p@h/db"}

    get_logger("storage").warning("connection retry", extra={**secrets, "attempt": 2})

    output = stream.getvalue()
    for value in secrets.values():
        assert value not in output
    [record] = _records(stream)
    assert all(record[key] == REDACTED for key in secrets)
    assert record["attempt"] == 2


def test_exceptions_log_type_and_code_but_not_message(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)
    private_text = "user said: my private medical appointment"

    try:
        raise PersistenceError(private_text)
    except PersistenceError:
        get_logger("storage").exception("Write failed")

    output = stream.getvalue()
    assert private_text not in output
    assert "Traceback" not in output
    [record] = _records(stream)
    assert record["error_type"] == "PersistenceError"
    assert record["error_code"] == "PERSISTENCE_ERROR"


def test_extra_fields_cannot_override_core_fields(valid_env: dict[str, str]) -> None:
    stream = io.StringIO()
    _configure(stream)

    get_logger("ingestion").info("real message", extra={"level": "CRITICAL", "service": "fake"})

    [record] = _records(stream)
    assert record["level"] == "INFO"
    assert record["service"] == "raven-memory-engine"


def test_configured_level_is_respected(
    valid_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}LOG_LEVEL", "WARNING")
    stream = io.StringIO()
    _configure(stream)

    get_logger("ingestion").info("hidden")
    get_logger("ingestion").warning("shown")

    assert [record["message"] for record in _records(stream)] == ["shown"]


def test_root_logger_is_never_modified(valid_env: dict[str, str]) -> None:
    root = logging.getLogger()
    handlers_before, level_before = list(root.handlers), root.level

    logger = _configure(io.StringIO())

    assert root.handlers == handlers_before
    assert root.level == level_before
    assert logger.propagate is False


def test_configuration_is_idempotent(valid_env: dict[str, str]) -> None:
    first, second = io.StringIO(), io.StringIO()
    _configure(first)
    logger = _configure(second)

    get_logger("ingestion").info("once")

    assert len(logger.handlers) == 1
    assert first.getvalue() == ""
    assert len(_records(second)) == 1


@pytest.mark.parametrize("component", ["", ".ingestion", "ingestion."])
def test_get_logger_rejects_invalid_component_names(component: str) -> None:
    with pytest.raises(ValueError, match="component"):
        get_logger(component)
