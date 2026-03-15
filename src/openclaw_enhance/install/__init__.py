"""Install package for openclaw-enhance.

Provides managed lifecycle for OpenClaw hooks, extensions, and agents.
"""

from openclaw_enhance.install.installer import (
    InstallError,
    InstallResult,
    get_install_status,
    install,
    preflight_checks,
)
from openclaw_enhance.install.lock import (
    InstallLock,
    InstallLockError,
    get_lock_info,
    is_locked,
    wait_for_lock,
)
from openclaw_enhance.install.manifest import (
    ComponentInstall,
    InstallManifest,
    is_installed,
    load_manifest,
    save_manifest,
)
from openclaw_enhance.install.uninstaller import (
    UninstallError,
    UninstallResult,
    is_symmetric_install_uninstall,
    uninstall,
)

__all__ = [
    # Installer
    "install",
    "preflight_checks",
    "get_install_status",
    "InstallResult",
    "InstallError",
    # Uninstaller
    "uninstall",
    "is_symmetric_install_uninstall",
    "UninstallResult",
    "UninstallError",
    # Lock
    "InstallLock",
    "InstallLockError",
    "is_locked",
    "get_lock_info",
    "wait_for_lock",
    # Manifest
    "InstallManifest",
    "ComponentInstall",
    "load_manifest",
    "save_manifest",
    "is_installed",
]
