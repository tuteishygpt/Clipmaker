"""JSON file repository with file locking for thread safety."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, TypeVar, Generic
from contextlib import contextmanager

T = TypeVar("T")


class FileLock:
    """Simple file-based locking mechanism using threading locks."""
    
    _locks: dict[str, threading.RLock] = {}
    _global_lock = threading.Lock()
    
    @classmethod
    def get_lock(cls, path: str) -> threading.RLock:
        """Get or create a lock for the given path."""
        with cls._global_lock:
            if path not in cls._locks:
                cls._locks[path] = threading.RLock()
            return cls._locks[path]


class JsonRepository:
    """Repository for reading and writing JSON files with locking."""
    
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
    
    @contextmanager
    def _locked_file(self, path: Path):
        """Context manager for thread-safe file access."""
        lock = FileLock.get_lock(str(path))
        with lock:
            yield path
    
    def load(self, relative_path: str, default: Any = None) -> Any:
        """Load JSON from a file, returning default if not found."""
        path = self.base_path / relative_path
        with self._locked_file(path):
            if not path.exists():
                return default
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default
    
    def save(self, relative_path: str, data: Any) -> None:
        """Save data to a JSON file."""
        path = self.base_path / relative_path
        with self._locked_file(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
    
    def update(self, relative_path: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Atomically update a JSON file with new values."""
        path = self.base_path / relative_path
        with self._locked_file(path):
            data = {}
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    data = {}
            
            if isinstance(data, dict):
                data.update(updates)
            else:
                data = updates
            
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return data
    
    def exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
        return (self.base_path / relative_path).exists()
    
    def delete(self, relative_path: str) -> bool:
        """Delete a file if it exists."""
        path = self.base_path / relative_path
        with self._locked_file(path):
            if path.exists():
                path.unlink()
                return True
            return False
