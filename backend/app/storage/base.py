from abc import ABC, abstractmethod
from typing import BinaryIO, Generator, Optional


class EvidenceStorageProvider(ABC):
    """Abstract interface for evidence object storage."""

    @abstractmethod
    def save(self, data: bytes, storage_key: str) -> str:
        """Store binary evidence data and return normalized storage key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieve binary evidence data by storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if an evidence artifact exists by storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Safely delete an evidence artifact by storage key."""
        pass

    @abstractmethod
    def get_absolute_path(self, storage_key: str) -> str:
        """Resolve the verified absolute filesystem path (if local)."""
        pass