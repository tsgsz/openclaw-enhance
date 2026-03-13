from openclaw_enhance.runtime.support_matrix import SupportError, validate_support_matrix


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
