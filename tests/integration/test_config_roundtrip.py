import json
from pathlib import Path

from openclaw_enhance.runtime.config_patch import apply_owned_config_patch


def test_config_roundtrip_owned_keys_and_backup_restore(tmp_path: Path) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "openclawEnhance": {
                    "enabled": False,
                    "limits": {"maxAgents": 2},
                },
                "telemetry": {"enabled": True},
            }
        ),
        encoding="utf-8",
    )

    apply_owned_config_patch(
        config_path,
        {
            "openclawEnhance": {
                "enabled": True,
                "limits": {"maxAgents": 4},
            },
            "telemetry": {"enabled": False},
        },
    )
    patched = json.loads(config_path.read_text(encoding="utf-8"))

    assert patched["openclawEnhance"]["enabled"] is True
    assert patched["openclawEnhance"]["limits"]["maxAgents"] == 4
    assert patched["telemetry"]["enabled"] is True
    assert (tmp_path / "openclaw.json.bak").exists()

    try:
        apply_owned_config_patch(
            config_path,
            {"openclawEnhance": {"enabled": False}},
            fail_on_write=True,
        )
    except Exception:
        pass

    after_failure = json.loads(config_path.read_text(encoding="utf-8"))
    assert after_failure == patched
