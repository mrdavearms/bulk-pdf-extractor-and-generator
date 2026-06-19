# tests/test_auto_update.py
from models import AppSettings


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
