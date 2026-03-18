"""Shared fixtures for integration tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _stub_openclaw_cli():
    """Prevent integration tests from calling real openclaw CLI."""
    mock_result = type("Result", (), {"returncode": 0, "stdout": "[]", "stderr": ""})()
    with patch(
        "openclaw_enhance.install.installer._run_openclaw_cli",
        return_value=mock_result,
    ):
        yield
