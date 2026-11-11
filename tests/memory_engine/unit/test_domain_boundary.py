"""Plan 8.1 initial test 6: domain-layer independence from infrastructure.

Parses source files instead of importing them, so a forbidden import is caught
even if the forbidden package is not installed.
"""

import ast
from pathlib import Path

import pytest

import memory_engine

PACKAGE_ROOT = Path(memory_engine.__file__).parent

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "pgvector",
    "celery",
    "kombu",
    "pika",
    "boto3",
    "botocore",
    "aioboto3",
    "httpx",
    "requests",
    "redis",
    "memory_engine.infrastructure",
)

DOMAIN_ALLOWED_INTERNAL: tuple[str, ...] = ("memory_engine.domain", "memory_engine.exceptions")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise AssertionError(f"Relative import in {path}; use absolute imports")
            if node.module:
                found.add(node.module)
    return found


def _matches(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def _python_files(package: str) -> list[Path]:
    files = sorted((PACKAGE_ROOT / package).rglob("*.py"))
    assert files, f"No source files found for {package}; the boundary check would be vacuous"
    return files


def test_domain_has_no_infrastructure_imports() -> None:
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("domain")
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES)
    ]
    assert violations == []


def test_domain_depends_only_on_domain_and_exceptions() -> None:
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("domain")
        for module in _imports(path)
        if _matches(module, ("memory_engine",)) and not _matches(module, DOMAIN_ALLOWED_INTERNAL)
    ]
    assert violations == []


def test_personal_domain_depends_only_on_the_shared_kernel() -> None:
    allowed = (*DOMAIN_ALLOWED_INTERNAL, "memory_engine.personal.domain")
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("personal/domain")
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES)
        or (_matches(module, ("memory_engine",)) and not _matches(module, allowed))
    ]
    assert violations == []


def test_personal_application_never_imports_infrastructure() -> None:
    # 7.1 section 23.1: application depends on ports, never on adapters.
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("personal/application")
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES)
        or _matches(module, ("memory_engine.interfaces", "memory_engine.documents"))
    ]
    assert violations == []


def test_documents_domain_depends_only_on_the_shared_kernel() -> None:
    allowed = (*DOMAIN_ALLOWED_INTERNAL, "memory_engine.documents.domain")
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("documents/domain")
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES)
        or (_matches(module, ("memory_engine",)) and not _matches(module, allowed))
    ]
    assert violations == []


def test_documents_application_never_imports_infrastructure() -> None:
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("documents/application")
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES) or _matches(module, ("memory_engine.interfaces",))
    ]
    assert violations == []


@pytest.mark.parametrize("package", ["documents", "infrastructure/persistence/documents"])
def test_document_intelligence_never_imports_personal_memory(package: str) -> None:
    # 7.1 section 23.1: the dependency between the two domains points one way.
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files(package)
        for module in _imports(path)
        if _matches(
            module, ("memory_engine.personal", "memory_engine.infrastructure.persistence.personal")
        )
    ]
    assert violations == []


def test_infrastructure_never_imports_interfaces() -> None:
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files("infrastructure")
        for module in _imports(path)
        if _matches(module, ("memory_engine.interfaces",))
    ]
    assert violations == []


def test_only_the_messaging_adapter_imports_the_broker_libraries() -> None:
    # 8.3 step 4: Celery, kombu and amqp stay inside infrastructure/messaging.
    messaging = PACKAGE_ROOT / "infrastructure" / "messaging"
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
        if messaging not in path.parents
        for module in _imports(path)
        if _matches(module, ("celery", "kombu", "amqp"))
    ]
    assert violations == []


@pytest.mark.parametrize("package", ["exceptions", "config", "observability"])
def test_foundation_packages_have_no_infrastructure_imports(package: str) -> None:
    violations = [
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in _python_files(package)
        for module in _imports(path)
        if _matches(module, FORBIDDEN_PREFIXES)
    ]
    assert violations == []


def test_boundary_checker_detects_a_violation(tmp_path: Path) -> None:
    offending = tmp_path / "bad.py"
    offending.write_text("from sqlalchemy.orm import Session\nimport celery\n", "utf-8")
    assert {module for module in _imports(offending) if _matches(module, FORBIDDEN_PREFIXES)} == {
        "sqlalchemy.orm",
        "celery",
    }
