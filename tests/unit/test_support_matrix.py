from unittest.mock import patch

from openclaw_enhance.runtime.support_matrix import (
    SupportError,
    validate_python_version,
    validate_support_matrix,
)


def test_validate_support_matrix_accepts_2026_3_x_on_macos() -> None:
    validate_support_matrix(openclaw_version="2026.3.9", platform_name="darwin")


def test_validate_support_matrix_accepts_2026_3_x_on_linux() -> None:
    validate_support_matrix(openclaw_version="2026.3.0", platform_name="linux")


def test_validate_support_matrix_rejects_unsupported_version() -> None:
    try:
        validate_support_matrix(openclaw_version="2026.4.0", platform_name="darwin")
    except SupportError as exc:
        assert "unsupported" in str(exc).lower()
        assert "2026.3.x" in str(exc)
    else:
        raise AssertionError("Expected SupportError")


def test_validate_support_matrix_rejects_unsupported_os() -> None:
    try:
        validate_support_matrix(openclaw_version="2026.3.2", platform_name="win32")
    except SupportError as exc:
        assert "unsupported" in str(exc).lower()
        assert "darwin/linux" in str(exc)
    else:
        raise AssertionError("Expected SupportError")


def test_validate_python_version_accepts_supported_version() -> None:
    # Current Python (3.10+) should pass
    validate_python_version()


def test_validate_python_version_rejects_old_version() -> None:
    from types import SimpleNamespace

    old_version_info = SimpleNamespace(major=3, minor=9, micro=0)
    with patch("sys.version_info", old_version_info):
        try:
            validate_python_version()
        except SupportError as exc:
            assert "python" in str(exc).lower()
            assert "3.10" in str(exc)
            assert "3.9" in str(exc)
        else:
            raise AssertionError("Expected SupportError")
