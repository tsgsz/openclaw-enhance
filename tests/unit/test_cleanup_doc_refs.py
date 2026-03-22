from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_install_docs_do_not_reference_wrapper_monitor_script() -> None:
    install_doc = (ROOT / "docs" / "install.md").read_text(encoding="utf-8")
    troubleshooting_doc = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")

    assert "scripts/monitor_runtime.py" not in install_doc
    assert "scripts/monitor_runtime.py" not in troubleshooting_doc
