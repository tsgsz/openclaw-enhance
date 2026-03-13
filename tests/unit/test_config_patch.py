import json
from pathlib import Path

from openclaw_enhance.runtime.config_patch import ConfigPatchError, apply_owned_config_patch


def test_apply_owned_config_patch_updates_only_owned_namespace(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "theme": "light",
                "openclawEnhance": {"enabled": False, "timeoutSeconds": 10},
            }
        ),
        encoding="utf-8",
    )

    result = apply_owned_config_patch(
        config_path,
        {
            "openclawEnhance": {"enabled": True, "timeoutSeconds": 30},
            "theme": "dark",
        },
    )

    assert result.changed_keys == ["openclawEnhance.enabled", "openclawEnhance.timeoutSeconds"]
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert updated["theme"] == "light"
    assert updated["openclawEnhance"]["enabled"] is True
    assert updated["openclawEnhance"]["timeoutSeconds"] == 30


def test_apply_owned_config_patch_restores_backup_when_write_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    original = {"openclawEnhance": {"enabled": False}, "theme": "light"}
    config_path.write_text(json.dumps(original), encoding="utf-8")

    try:
        apply_owned_config_patch(
            config_path,
            {"openclawEnhance": {"enabled": True}},
            fail_on_write=True,
        )
    except ConfigPatchError as exc:
        assert "failed" in str(exc).lower()
    else:
        raise AssertionError("Expected ConfigPatchError")

    restored = json.loads(config_path.read_text(encoding="utf-8"))
    assert restored == original
    backup_path = tmp_path / "config.json.bak"
    assert backup_path.exists()
