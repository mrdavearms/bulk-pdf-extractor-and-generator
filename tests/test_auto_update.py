# tests/test_auto_update.py
import inspect

from models import AppSettings
from pdf_generator import BulkPDFGenerator


def test_appsettings_has_last_update_check_default():
    s = AppSettings(templates_directory="/tmp/x")
    assert s.last_update_check == ""


def test_appsettings_roundtrips_last_update_check():
    s = AppSettings(templates_directory="/tmp/x", last_update_check="2026-06-20")
    restored = AppSettings.from_json(s.to_json())
    assert restored.last_update_check == "2026-06-20"


def test_appsettings_loads_old_json_without_last_update_check():
    # Settings files written before this field existed must still load.
    old = '{"templates_directory": "/tmp/x", "school_name": "WHS"}'
    s = AppSettings.from_json(old)
    assert s.last_update_check == ""
    assert s.school_name == "WHS"


from pdf_generator import _should_check_for_update


def test_check_due_when_never_checked():
    assert _should_check_for_update("", "2026-06-20") is True


def test_check_not_due_when_already_checked_today():
    assert _should_check_for_update("2026-06-20", "2026-06-20") is False


def test_check_due_when_last_check_was_a_previous_day():
    assert _should_check_for_update("2026-06-19", "2026-06-20") is True


def test_check_due_when_stored_value_is_malformed():
    # A corrupt stored value should not silently disable checking forever.
    assert _should_check_for_update("garbage", "2026-06-20") is True


def test_startup_update_path_is_nonmodal():
    # A startup check must never use a modal pop-up (macOS freeze risk).
    src = (inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
           + inspect.getsource(BulkPDFGenerator._show_startup_update_result))
    assert "messagebox" not in src


def test_startup_update_check_is_backgrounded():
    src = inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
    assert "daemon=True" in src        # runs off the UI thread
    assert "root.after" in src         # result dispatched back to UI thread


def test_startup_update_respects_daily_throttle():
    src = inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
    assert "_should_check_for_update" in src
    assert "last_update_check" in src


# ── Retry behaviour ──────────────────────────────────────────────────────────
# A check that never reached GitHub must not use up the day's only attempt.
# Otherwise a laptop opened before the wifi connects — or a school network that
# blocks the request — leaves the teacher silently un-notified for weeks.

from unittest.mock import MagicMock, patch

from pdf_generator import BulkPDFGenerator


def _headless_app(tmp_path, last_check=""):
    """A BulkPDFGenerator with no GUI — __init__ is skipped deliberately."""
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.settings = AppSettings(templates_directory=str(tmp_path),
                               last_update_check=last_check)
    app.settings_file = str(tmp_path / "settings.json")
    app._build_info = ("abc1234", "07 Sep 2026", "v2.15")
    app.root = MagicMock()
    return app


def test_failed_check_does_not_consume_the_day(tmp_path):
    app = _headless_app(tmp_path)
    app._show_startup_update_result({"status": "error", "message": "offline"})
    assert app.settings.last_update_check == "", (
        "a failed check must leave the date unset so the next launch retries")


def test_successful_check_records_today(tmp_path):
    from datetime import datetime
    app = _headless_app(tmp_path)
    app._show_startup_update_result({"status": "up_to_date", "latest": "v2.15"})
    assert app.settings.last_update_check == datetime.now().date().isoformat()


def test_update_available_records_today_and_shows_banner(tmp_path):
    from datetime import datetime
    app = _headless_app(tmp_path)
    app._update_banner = MagicMock()
    app._update_banner_lbl = MagicMock()
    app._content_frame = MagicMock()
    app._show_startup_update_result({
        "status": "update_available", "latest": "v2.16",
        "html_url": "https://example.invalid/tag/v2.16"})
    assert app.settings.last_update_check == datetime.now().date().isoformat()
    assert app._update_url == "https://example.invalid/tag/v2.16"
    app._update_banner.pack.assert_called_once()


def test_only_one_check_attempt_per_launch(tmp_path):
    """The in-session guard replaces the old record-before-the-call throttle."""
    app = _headless_app(tmp_path)
    with patch("pdf_generator.threading.Thread") as thread:
        app._maybe_auto_check_update()
        app._maybe_auto_check_update()
    assert thread.call_count == 1


def test_no_check_when_already_checked_today(tmp_path):
    from datetime import datetime
    today = datetime.now().date().isoformat()
    app = _headless_app(tmp_path, last_check=today)
    with patch("pdf_generator.threading.Thread") as thread:
        app._maybe_auto_check_update()
    assert thread.call_count == 0


def test_no_check_on_a_source_run(tmp_path):
    app = _headless_app(tmp_path)
    app._build_info = ("abc1234", "local build", "dev")
    with patch("pdf_generator.threading.Thread") as thread:
        app._maybe_auto_check_update()
    assert thread.call_count == 0
