from pathlib import Path

OPENCLAW_HOME_DIRNAME = ".openclaw"
ENHANCE_DIRNAME = "openclaw-enhance"
RUNTIME_STATE_FILENAME = "runtime-state.json"
CONFIG_BACKUP_FILENAME = "config.json.bak"


def managed_root(user_home: Path | None = None) -> Path:
    base_home = user_home if user_home is not None else Path.home()
    return base_home / OPENCLAW_HOME_DIRNAME / ENHANCE_DIRNAME


def runtime_state_file(user_home: Path | None = None) -> Path:
    return managed_root(user_home) / RUNTIME_STATE_FILENAME


def config_backup_file(user_home: Path | None = None) -> Path:
    return managed_root(user_home) / CONFIG_BACKUP_FILENAME


def ensure_managed_directories(user_home: Path | None = None) -> Path:
    root = managed_root(user_home)
    root.mkdir(parents=True, exist_ok=True)
    return root
