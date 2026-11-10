"""Plan 8.1 initial test 1: project imports."""

import importlib
from importlib.metadata import version
from pathlib import Path

import pytest

import memory_engine


@pytest.mark.parametrize(
    "module",
    [
        "memory_engine",
        "memory_engine.config",
        "memory_engine.config.settings",
        "memory_engine.domain",
        "memory_engine.domain.errors",
        "memory_engine.exceptions",
        "memory_engine.exceptions.base",
        "memory_engine.observability",
        "memory_engine.observability.context",
        "memory_engine.observability.logging",
    ],
)
def test_module_imports(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_version_matches_installed_distribution() -> None:
    assert memory_engine.__version__ == version("raven-memory-engine")
    assert memory_engine.__version__ != "0.0.0"


def test_package_is_marked_typed() -> None:
    assert (Path(memory_engine.__file__).parent / "py.typed").is_file()
