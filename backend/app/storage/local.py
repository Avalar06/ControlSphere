import os
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.storage.base import EvidenceStorageProvider


class LocalStorageProvider(EvidenceStorageProvider):
    """Local filesystem storage provider with path traversal confinement."""

    def __init__(self, root_dir: Optional[str] = None):
        self.root_path = Path(root_dir or settings.EVIDENCE_STORAGE_ROOT).resolve()
        # Ensure root directory exists
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> Path:
        """Resolve and verify that the target path remains strictly within the storage root."""
        # Normalize slashes and strip leading separators
        clean_key = storage_key.replace("\\", "/").lstrip("/")
        target_path = (self.root_path / clean_key).resolve()

        # Mathematically strict path traversal confinement check
        try:
            if not target_path.is_relative_to(self.root_path):
                raise ValueError(f"Path traversal detected: {storage_key} resolves outside storage root.")
        except AttributeError:
            # Fallback for Python < 3.9
            if self.root_path not in target_path.parents and target_path != self.root_path:
                raise ValueError(f"Path traversal detected: {storage_key} resolves outside storage root.")

        return target_path


    def save(self, data: bytes, storage_key: str) -> str:
        target_path = self._resolve_safe_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temporary file
        temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
            temp_path.replace(target_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        return storage_key

    def get(self, storage_key: str) -> bytes:
        target_path = self._resolve_safe_path(storage_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Evidence artifact '{storage_key}' not found on storage.")
        with open(target_path, "rb") as f:
            return f.read()

    def exists(self, storage_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(storage_key)
            return target_path.is_file()
        except ValueError:
            return False

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_safe_path(storage_key)
        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    def get_absolute_path(self, storage_key: str) -> str:
        target_path = self._resolve_safe_path(storage_key)
        return str(target_path)


_default_provider: Optional[EvidenceStorageProvider] = None


def get_storage_provider() -> EvidenceStorageProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = LocalStorageProvider()
    return _default_provider