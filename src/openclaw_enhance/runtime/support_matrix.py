import re
import sys
from pathlib import Path

SUPPORTED_VERSION_PATTERN = re.compile(r"^2026\.3\.\d+$")
SUPPORTED_PLATFORMS = {"darwin", "linux"}
MIN_PYTHON_VERSION = (3, 10)


class SupportError(RuntimeError):
    pass


def validate_python_version() -> None:
    current = (sys.version_info.major, sys.version_info.minor)
    if current < MIN_PYTHON_VERSION:
        raise SupportError(
            f"Unsupported Python version '{sys.version_info.major}.{sys.version_info.minor}'. "
            f"Supported: >={MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
        )


def validate_support_matrix(openclaw_version: str, platform_name: str | None = None) -> None:
    target_platform = platform_name or sys.platform
    if target_platform not in SUPPORTED_PLATFORMS:
        raise SupportError(f"Unsupported platform '{target_platform}'. Supported: darwin/linux")
    if not SUPPORTED_VERSION_PATTERN.match(openclaw_version):
        raise SupportError(
            f"Unsupported OpenClaw version '{openclaw_version}'. Supported: 2026.3.x"
        )


def read_openclaw_version(openclaw_home: Path) -> str:
    version_file = openclaw_home / "VERSION"
    if not version_file.exists():
        raise SupportError(f"unsupported/missing-home: missing VERSION file under {openclaw_home}")
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise SupportError("Unsupported OpenClaw version ''. Supported: 2026.3.x")
    return version


def validate_environment(openclaw_home: Path, platform_name: str | None = None) -> None:
    validate_python_version()
    if not openclaw_home.exists() or not openclaw_home.is_dir():
        raise SupportError(f"unsupported/missing-home: {openclaw_home}")
    version = read_openclaw_version(openclaw_home)
    validate_support_matrix(version, platform_name)
