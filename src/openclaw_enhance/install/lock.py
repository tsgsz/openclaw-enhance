"""Install locking mechanism to prevent concurrent installations.

Provides filesystem-based locking with timeout and stale lock detection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO, Any

LOCK_FILENAME = ".install.lock"
LOCK_TIMEOUT_SECONDS = 300  # 5 minutes
STALE_LOCK_SECONDS = 600  # 10 minutes


@dataclass
class LockInfo:
    """Information about an active lock."""

    pid: int
    created_at: datetime
    operation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pid": self.pid,
            "created_at": self.created_at.isoformat(),
            "operation": self.operation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockInfo:
        """Create from dictionary."""
        return cls(
            pid=data["pid"],
            created_at=datetime.fromisoformat(data["created_at"]),
            operation=data["operation"],
        )


class InstallLockError(RuntimeError):
    """Raised when lock cannot be acquired."""

    pass


class InstallLock:
    """Filesystem-based install lock with timeout support."""

    def __init__(
        self,
        managed_root: Path,
        timeout_seconds: float = LOCK_TIMEOUT_SECONDS,
        stale_seconds: float = STALE_LOCK_SECONDS,
    ):
        self.managed_root = managed_root
        self.lock_path = managed_root / LOCK_FILENAME
        self.timeout_seconds = timeout_seconds
        self.stale_seconds = stale_seconds
        self._acquired = False
        self._lock_handle: IO[str] | None = None

    def _is_stale(self, info: LockInfo) -> bool:
        """Check if a lock is stale (old and likely abandoned)."""
        age = datetime.utcnow() - info.created_at
        return age.total_seconds() > self.stale_seconds

    def _read_lock_info(self) -> LockInfo | None:
        """Read lock info from file if it exists."""
        if not self.lock_path.exists():
            return None
        try:
            import json

            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            return LockInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None

    def _write_lock_info(self, info: LockInfo) -> None:
        """Write lock info to file."""
        import json

        self.managed_root.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(
            json.dumps(info.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

    def _is_lock_holder_alive(self, info: LockInfo) -> bool:
        """Check if the process holding the lock is still alive."""
        import os
        import signal

        try:
            # Check if process exists
            os.kill(info.pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def acquire(self, operation: str = "install", blocking: bool = True) -> bool:
        """Acquire the install lock.

        Args:
            operation: Description of the operation acquiring the lock.
            blocking: If True, wait for the lock; if False, fail immediately.

        Returns:
            True if lock acquired, False otherwise (only when blocking=False).

        Raises:
            InstallLockError: If lock cannot be acquired.
        """
        import os

        start_time = time.time()

        while True:
            existing_info = self._read_lock_info()

            if existing_info is None:
                # No lock exists, acquire it
                break

            if existing_info.pid == os.getpid():
                # We already hold the lock
                self._acquired = True
                return True

            if self._is_stale(existing_info) or not self._is_lock_holder_alive(existing_info):
                # Lock is stale or process is dead, steal it
                try:
                    self.lock_path.unlink()
                except OSError:
                    pass
                break

            if not blocking:
                return False

            if time.time() - start_time > self.timeout_seconds:
                raise InstallLockError(
                    f"Timeout waiting for install lock (held by PID {existing_info.pid}, "
                    f"operation: {existing_info.operation})"
                )

            time.sleep(0.5)

        # Acquire the lock
        info = LockInfo(
            pid=os.getpid(),
            created_at=datetime.utcnow(),
            operation=operation,
        )
        self._write_lock_info(info)
        self._acquired = True
        return True

    def release(self) -> None:
        """Release the install lock."""
        if not self._acquired:
            return

        try:
            if self.lock_path.exists():
                info = self._read_lock_info()
                if info and info.pid == self._lock_pid():
                    self.lock_path.unlink()
        except OSError:
            pass
        finally:
            self._acquired = False

    def _lock_pid(self) -> int:
        """Get current process PID."""
        import os

        return os.getpid()

    def __enter__(self) -> InstallLock:
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.release()


def is_locked(managed_root: Path) -> bool:
    """Check if there's an active install lock."""
    lock_path = managed_root / LOCK_FILENAME
    if not lock_path.exists():
        return False

    try:
        import json

        data = json.loads(lock_path.read_text(encoding="utf-8"))
        info = LockInfo.from_dict(data)

        lock = InstallLock(managed_root)
        if lock._is_stale(info):
            return False

        return lock._is_lock_holder_alive(info)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return False


def get_lock_info(managed_root: Path) -> LockInfo | None:
    """Get information about the current lock if any."""
    lock_path = managed_root / LOCK_FILENAME
    if not lock_path.exists():
        return None

    try:
        import json

        data = json.loads(lock_path.read_text(encoding="utf-8"))
        return LockInfo.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


def wait_for_lock(
    managed_root: Path,
    timeout_seconds: float = LOCK_TIMEOUT_SECONDS,
    poll_interval: float = 0.5,
) -> bool:
    """Wait for the install lock to be released.

    Args:
        managed_root: Path to the managed root directory.
        timeout_seconds: Maximum time to wait.
        poll_interval: Time between checks.

    Returns:
        True if lock is released, False if timeout.
    """
    start_time = time.time()
    while is_locked(managed_root):
        if time.time() - start_time > timeout_seconds:
            return False
        time.sleep(poll_interval)
    return True
