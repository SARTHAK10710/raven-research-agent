"""Quality: the English-first check against its synthetic dataset (8.4 step 1; G6).

Also validates every dataset file under ``data/`` (format owner-approved).
"""

from pathlib import Path

import pytest
from tests.memory_engine.quality.datasets import (
    Case,
    DatasetError,
    dataset_files,
    load,
    load_dataset,
)

from memory_engine.config.settings import ExtractionSettings
from memory_engine.personal.application.language import (
    UNSUPPORTED_LANGUAGE,
    assess,
    language_policy,
)

POLICY = language_policy(ExtractionSettings())
LANGUAGE_V1 = load_dataset("language", 1)


@pytest.mark.parametrize("path", dataset_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_every_dataset_file_is_valid(path: Path) -> None:
    assert load(path)


@pytest.mark.parametrize("case", LANGUAGE_V1, ids=lambda c: c.id)
def test_the_language_check_matches_every_labelled_case(case: Case) -> None:
    result = assess(case.input["texts"], POLICY)
    assert result.english is case.expected["english"], case.notes
    assert (result.reason_code is None) is result.english
    if not result.english:
        assert result.reason_code == UNSUPPORTED_LANGUAGE


def test_the_language_dataset_covers_both_labels_and_several_scripts() -> None:
    labels = [c.expected["english"] for c in LANGUAGE_V1]
    assert labels.count(True) >= 10 and labels.count(False) >= 10


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json\n", "not JSON"),
        ("[1]\n", "not an object"),
        ('{"schema_version": "1", "id": "x", "input": {}}\n', "unexpected keys"),
        (
            '{"schema_version": "2", "id": "x", "input": {}, "expected": {}}\n',
            "schema_version",
        ),
        (
            '{"schema_version": "1", "id": "x", "input": {}, "expected": {}}\n'
            '{"schema_version": "1", "id": "x", "input": {}, "expected": {}}\n',
            "duplicate id",
        ),
        ('{"schema_version": "1", "id": "x", "input": [], "expected": {}}\n', "objects"),
        ("\n", "empty"),
    ],
)
def test_malformed_datasets_are_refused(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "v1.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DatasetError, match=message):
        load(path)
