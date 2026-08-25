import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple
from app.core.config import settings


class FileSecurityError(ValueError):
    """Raised when an uploaded file fails security or format validation."""
    pass


MAGIC_SIGNATURES = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
}

MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize original client-supplied filename, stripping path components and dangerous chars."""
    if not filename:
        return "unnamed_artifact"

    # Strip directory separators and null bytes
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.replace("\x00", "")

    # Remove any non-whitelisted characters
    cleaned = re.sub(r'[^a-zA-Z0-9._\- ]', '_', cleaned)

    # Prevent hidden files or relative traversal tricks
    cleaned = cleaned.lstrip(".")
    if not cleaned:
        cleaned = "unnamed_artifact"

    # Truncate length
    if len(cleaned) > 200:
        base, ext = os.path.splitext(cleaned)
        cleaned = base[:190] + ext

    return cleaned


def validate_file_size(size_in_bytes: int) -> None:
    """Validate that the file size is non-zero and within configured maximum limit."""
    if size_in_bytes <= 0:
        raise FileSecurityError("Zero-byte empty files cannot be accepted as evidence.")

    max_bytes = settings.MAX_EVIDENCE_FILE_SIZE_MB * 1024 * 1024
    if size_in_bytes > max_bytes:
        raise FileSecurityError(
            f"File size ({size_in_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {settings.MAX_EVIDENCE_FILE_SIZE_MB} MB."
        )


def validate_extension(filename: str) -> str:
    """Extract and validate normalized file extension against the allowlist."""
    ext = Path(filename).suffix.lower()
    if not ext:
        raise FileSecurityError("Uploaded file has no extension. Please provide a supported file format.")

    if ext not in settings.ALLOWED_EVIDENCE_EXTENSIONS:
        raise FileSecurityError(
            f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EVIDENCE_EXTENSIONS)}"
        )

    return ext


def verify_content_type(file_bytes: bytes, ext: str, declared_content_type: str) -> str:
    """Inspect magic bytes / content structure to prevent MIME spoofing and disguised executables."""
    # 1. Check known binary magic signatures
    if ext in MAGIC_SIGNATURES:
        signatures = MAGIC_SIGNATURES[ext]
        matches = any(file_bytes.startswith(sig) for sig in signatures)
        if not matches:
            raise FileSecurityError(
                f"File content does not match expected binary signature for extension '{ext}'."
            )

    # 2. Check text formats (.csv, .txt)
    elif ext in [".csv", ".txt"]:
        sample = file_bytes[:4096]
        if b"\x00" in sample:
            raise FileSecurityError(
                f"File claiming to be '{ext}' contains embedded binary null bytes."
            )
        try:
            # Attempt to decode sample as UTF-8 or ASCII
            sample.decode("utf-8")
        except UnicodeDecodeError:
            raise FileSecurityError(
                f"File claiming to be '{ext}' contains non-text or binary data."
            )


    # Determine canonical content type
    return MIME_TYPE_MAP.get(ext, declared_content_type or "application/octet-stream")


def compute_sha256(file_bytes: bytes) -> str:
    """Compute cryptographic SHA-256 hash of the received raw bytes."""
    return hashlib.sha256(file_bytes).hexdigest().lower()


def generate_secure_storage_key(organization_id: int, extension: str) -> Tuple[str, str]:
    """Generate a server-controlled random storage key and stored filename."""
    now = datetime.now(timezone.utc)
    random_id = uuid.uuid4().hex
    clean_ext = extension.lstrip(".")
    stored_filename = f"{random_id}.{clean_ext}"
    storage_key = f"org_{organization_id}/{now.year}/{now.month:02d}/{stored_filename}"
    return storage_key, stored_filename