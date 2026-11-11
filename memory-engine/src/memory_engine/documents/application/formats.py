"""Actual-format detection for uploads (plan 8.3 sections 4.2 and 6.1; owner-approved, step 3).

Standard library only. The content decides the format; the filename extension
and any declared media type must agree with it or the upload is rejected.
Nothing is parsed or executed: PDFs are checked by header and trailer, DOCX by
the ZIP's file listing (never by reading XML), TXT by strict UTF-8 decoding.
Text extraction belongs to the document pipeline (Decision 13).

Every rejection raises :class:`IngestionRejectedError` with ``outcome`` and an
UPPER_SNAKE_CASE ``reason``; messages never contain file content.
"""

import io
import unicodedata
import zipfile

from memory_engine.documents.domain.vocabulary import DocumentMediaType
from memory_engine.exceptions import IngestionRejectedError

_EXTENSIONS = {
    ".pdf": DocumentMediaType.PDF,
    ".docx": DocumentMediaType.DOCX,
    ".txt": DocumentMediaType.TXT,
}
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .doc, and encrypted Office files
_ZIP_MAGIC = b"PK\x03\x04"
_PDF_WINDOW = 1024
_MAX_ZIP_ENTRIES = 10_000
_MAX_COMPRESSION_RATIO = 100  # per entry; protects against zip bombs
_MACRO_PARTS = ("vbaproject.bin", "vbadata.xml")


def reject(outcome: str, reason: str) -> IngestionRejectedError:
    return IngestionRejectedError(
        f"Upload rejected: {reason}", details={"outcome": outcome, "reason": reason}
    )


def _unsupported(reason: str = "UNSUPPORTED_FORMAT") -> IngestionRejectedError:
    return reject("unsupported_input", reason)


def _invalid(reason: str) -> IngestionRejectedError:
    return reject("invalid_input", reason)


def safe_filename(filename: str) -> str:
    """The display name to keep: last path component only, no control characters.

    Never used to build storage keys or paths (7.2 section 10).
    """
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = unicodedata.normalize("NFC", name)
    name = "".join(c for c in name if unicodedata.category(c) not in ("Cc", "Cf")).strip()
    if not name or name in (".", "..") or len(name) > 255:
        raise _invalid("INVALID_FILENAME")
    return name


def detect_media_type(data: bytes, *, max_bytes: int) -> DocumentMediaType:
    """The format the content actually has, or a rejection."""
    if not data:
        raise _invalid("EMPTY_FILE")
    if data.startswith(_OLE_MAGIC):
        raise _unsupported()
    if data.startswith(_ZIP_MAGIC):
        _check_docx(data, max_bytes=max_bytes)
        return DocumentMediaType.DOCX
    if b"%PDF-" in data[:_PDF_WINDOW]:
        if b"%%EOF" not in data[-_PDF_WINDOW:]:
            raise _invalid("MALFORMED_DOCUMENT")  # truncated or damaged
        return DocumentMediaType.PDF
    _check_text(data)
    return DocumentMediaType.TXT


def _check_docx(data: bytes, *, max_bytes: int) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
    except (zipfile.BadZipFile, ValueError) as err:
        raise _invalid("MALFORMED_DOCUMENT") from err
    if len(entries) > _MAX_ZIP_ENTRIES:
        raise _invalid("ARCHIVE_TOO_LARGE")
    names = {entry.filename.lower() for entry in entries}
    if "[content_types].xml" not in names or "word/document.xml" not in names:
        raise _unsupported()  # another ZIP-based format (spreadsheet, slides, archive)
    if any(name.rsplit("/", 1)[-1] in _MACRO_PARTS for name in names):
        raise _unsupported("MACROS_NOT_ALLOWED")
    if any(entry.flag_bits & 0x1 for entry in entries):
        raise _unsupported("ENCRYPTED_DOCUMENT")
    total = sum(entry.file_size for entry in entries)
    if total > 10 * max_bytes or any(
        entry.file_size > _MAX_COMPRESSION_RATIO * max(entry.compress_size, 1)
        and entry.file_size > 1024 * 1024
        for entry in entries
    ):
        raise _invalid("ARCHIVE_TOO_LARGE")


def _check_text(data: bytes) -> None:
    if b"\x00" in data:
        raise _unsupported()  # binary content
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise _unsupported("UNSUPPORTED_ENCODING") from err
    if not text.strip():
        raise _invalid("EMPTY_FILE")


def check_declared(
    detected: DocumentMediaType, *, filename: str, declared: DocumentMediaType | None
) -> None:
    """The extension and the declared type, when present, must match the content."""
    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[-1].lower()
        if _EXTENSIONS.get(extension) is not detected:
            raise _invalid("EXTENSION_MISMATCH")
    if declared is not None and declared is not detected:
        raise _invalid("MEDIA_TYPE_MISMATCH")
