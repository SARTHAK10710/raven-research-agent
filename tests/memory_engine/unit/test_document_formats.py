"""Phase 8.3 step 3: actual-format detection and filename handling (no I/O).

All files are synthetic and built in memory.
"""

import io
import zipfile

import pytest

from memory_engine.documents.application.formats import (
    check_declared,
    detect_media_type,
    safe_filename,
)
from memory_engine.documents.domain.vocabulary import DocumentMediaType
from memory_engine.exceptions import IngestionRejectedError

MIB = 1024 * 1024
PDF = b"%PDF-1.7\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"
TXT = "Synthetic notes: caf\u00e9 \u2014 r\u00e9sum\u00e9.\n".encode()


def docx(*extra: tuple[str, bytes], document: bool = True) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        if document:
            archive.writestr("word/document.xml", "<w:document/>")
        for name, data in extra:
            archive.writestr(name, data)
    return buffer.getvalue()


def _reason(data: bytes) -> tuple[str, str]:
    with pytest.raises(IngestionRejectedError) as caught:
        detect_media_type(data, max_bytes=25 * MIB)
    return caught.value.details["outcome"], caught.value.details["reason"]


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (PDF, DocumentMediaType.PDF),
        (b"\xef\xbb\xbf" + TXT, DocumentMediaType.TXT),  # UTF-8 with BOM
        (TXT, DocumentMediaType.TXT),
        (docx(), DocumentMediaType.DOCX),
    ],
)
def test_supported_formats_are_detected_from_content(
    data: bytes, expected: DocumentMediaType
) -> None:
    assert detect_media_type(data, max_bytes=25 * MIB) is expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"", ("invalid_input", "EMPTY_FILE")),
        (b"  \n\t ", ("invalid_input", "EMPTY_FILE")),
        (PDF[:-8], ("invalid_input", "MALFORMED_DOCUMENT")),  # truncated: no %%EOF
        (b"PK\x03\x04 not really a zip", ("invalid_input", "MALFORMED_DOCUMENT")),
        (docx(document=False), ("unsupported_input", "UNSUPPORTED_FORMAT")),  # e.g. a workbook
        (
            docx(("word/vbaProject.bin", b"macro")),
            ("unsupported_input", "MACROS_NOT_ALLOWED"),
        ),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest", ("unsupported_input", "UNSUPPORTED_FORMAT")),
        (b"\x89PNG\r\n\x1a\n\x00\x00", ("unsupported_input", "UNSUPPORTED_FORMAT")),
        ("caf\u00e9".encode("latin-1"), ("unsupported_input", "UNSUPPORTED_ENCODING")),
    ],
)
def test_unsupported_damaged_or_empty_files_are_rejected(
    data: bytes, expected: tuple[str, str]
) -> None:
    assert _reason(data) == expected


def test_a_zip_bomb_is_refused_from_its_listing() -> None:
    bomb = docx(("word/media/blank.bin", b"\x00" * (8 * MIB)))  # compresses ~1000:1
    assert _reason(bomb) == ("invalid_input", "ARCHIVE_TOO_LARGE")


@pytest.mark.parametrize(
    ("filename", "detected", "declared", "reason"),
    [
        ("report.pdf", DocumentMediaType.DOCX, None, "EXTENSION_MISMATCH"),
        ("notes.md", DocumentMediaType.TXT, None, "EXTENSION_MISMATCH"),
        ("report.PDF", DocumentMediaType.PDF, DocumentMediaType.TXT, "MEDIA_TYPE_MISMATCH"),
    ],
)
def test_extension_and_declared_type_must_match_the_content(
    filename: str,
    detected: DocumentMediaType,
    declared: DocumentMediaType | None,
    reason: str,
) -> None:
    with pytest.raises(IngestionRejectedError) as caught:
        check_declared(detected, filename=filename, declared=declared)
    assert caught.value.details["reason"] == reason


def test_matching_or_missing_extensions_are_accepted() -> None:
    check_declared(DocumentMediaType.PDF, filename="Report.Pdf", declared=DocumentMediaType.PDF)
    check_declared(DocumentMediaType.TXT, filename="README", declared=None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.txt", "passwd.txt"),
        ("C:\\Users\\someone\\Report final.pdf", "Report final.pdf"),
        ("  notes\u200b.txt\x00 ", "notes.txt"),
    ],
)
def test_filenames_keep_only_a_safe_display_name(raw: str, expected: str) -> None:
    assert safe_filename(raw) == expected


@pytest.mark.parametrize("raw", ["", "  ", "folder/", "..", "a" * 300 + ".txt"])
def test_unusable_filenames_are_rejected(raw: str) -> None:
    with pytest.raises(IngestionRejectedError) as caught:
        safe_filename(raw)
    assert caught.value.details["reason"] == "INVALID_FILENAME"
