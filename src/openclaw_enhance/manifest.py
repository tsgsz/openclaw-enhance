"""Manifest module for openclaw-enhance v2 - tracks installed skills, hooks, and extensions."""

import json
from pathlib import Path

MANIFEST_PATH = Path.home() / ".openclaw" / "openclaw-enhance" / "manifest.json"
MANIFEST_VERSION = "2.0.0"


def _ensure_parent_dir() -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_manifest() -> dict:
    """Load the manifest from disk.

    Returns:
        dict: The manifest data, or empty dict if file doesn't exist.
    """
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(data: dict) -> None:
    """Save the manifest to disk.

    Args:
        data: The manifest data to save.
    """
    _ensure_parent_dir()
    MANIFEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_skill(name: str, location: str, version: str | None = None) -> dict:
    """Add a skill to the manifest.

    Args:
        name: Name of the skill.
        location: Path to the skill.
        version: Optional version string.

    Returns:
        dict: The updated manifest.
    """
    manifest = load_manifest()
    if "skills" not in manifest:
        manifest["skills"] = {}

    manifest["skills"][name] = {
        "name": name,
        "location": location,
        "version": version or "1.0.0",
    }

    # Ensure version field exists at root level
    if "version" not in manifest:
        manifest["version"] = MANIFEST_VERSION

    save_manifest(manifest)
    return manifest


def remove_skill(name: str) -> dict:
    """Remove a skill from the manifest.

    Args:
        name: Name of the skill to remove.

    Returns:
        dict: The updated manifest.
    """
    manifest = load_manifest()
    if "skills" in manifest and name in manifest["skills"]:
        del manifest["skills"][name]
        save_manifest(manifest)
    return manifest


def get_installed() -> dict:
    """Get the installed components summary.

    Returns:
        dict: Summary of installed skills, hooks, and extensions.
    """
    manifest = load_manifest()
    return {
        "version": manifest.get("version", MANIFEST_VERSION),
        "skills": list(manifest.get("skills", {}).keys()),
        "hooks": list(manifest.get("hooks", {}).keys()),
        "extension": list(manifest.get("extension", {}).keys()),
    }
