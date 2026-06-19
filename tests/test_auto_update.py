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
