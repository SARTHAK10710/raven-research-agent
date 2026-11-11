"""Versioned synthetic evaluation datasets (Decision 14; owner-approved format, 8.4 step 1).

Layout: ``data/<capability>/v<N>.jsonl``. Each line is one case::

    {"schema_version": "1", "id": "<unique>", "input": {...},
     "expected": {...}, "notes": "<optional>"}

All content is synthetic. A dataset version never changes once used in a
result; new cases go into a new version.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent / "data"
SCHEMA_VERSION = "1"
_KEYS = {"schema_version", "id", "input", "expected"}
_OPTIONAL = {"notes"}


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    input: dict[str, Any]
    expected: dict[str, Any]
    notes: str = ""


class DatasetError(ValueError):
    pass


def dataset_files() -> list[Path]:
    return sorted(DATA.glob("*/v*.jsonl"))


def load(path: Path) -> list[Case]:
    """Read and validate one dataset file."""
    cases: list[Case] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as err:
            raise DatasetError(f"{path.name}:{number}: not JSON") from err
        if not isinstance(record, dict):
            raise DatasetError(f"{path.name}:{number}: not an object")
        keys = set(record)
        if not keys >= _KEYS or keys - _KEYS - _OPTIONAL:
            raise DatasetError(f"{path.name}:{number}: unexpected keys")
        if record["schema_version"] != SCHEMA_VERSION:
            raise DatasetError(f"{path.name}:{number}: unsupported schema_version")
        case_id = record["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise DatasetError(f"{path.name}:{number}: missing or duplicate id")
        if not isinstance(record["input"], dict) or not isinstance(record["expected"], dict):
            raise DatasetError(f"{path.name}:{number}: input and expected must be objects")
        seen.add(case_id)
        cases.append(Case(case_id, record["input"], record["expected"], record.get("notes", "")))
    if not cases:
        raise DatasetError(f"{path.name}: empty dataset")
    return cases


def load_dataset(capability: str, version: int) -> list[Case]:
    return load(DATA / capability / f"v{version}.jsonl")
