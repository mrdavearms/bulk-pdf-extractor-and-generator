"""The exported workbook is the artifact teachers actually type into.
If it doesn't tell them what's valid, the app's strict validation is a trap."""
import pandas as pd
import pytest

from models import PDFField
from pdf_generator import BulkPDFGenerator


def _app(fields):
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.analyzed_fields = fields
    return app


def _field(name, ftype="Text", **kw):
    return PDFField(
        field_name=name, field_type=ftype, page=1,
        length=kw.pop("length", None), is_combed=kw.pop("is_combed", False),
        combed_fields=kw.pop("combed_fields", []), rect=(0, 0, 10, 10), **kw
    )


def test_allowed_values_spell_out_radio_options():
    app = _app([])
    f = _field("Session", "RadioButton", on_states=["Morning", "Afternoon"])
    assert "Morning" in app.field_allowed_values(f)
    assert "Afternoon" in app.field_allowed_values(f)


def test_allowed_values_spell_out_dropdown_options():
    app = _app([])
    f = _field("State", "ComboBox", options=["VIC", "NSW"])
    assert "VIC" in app.field_allowed_values(f)


def test_allowed_values_explain_checkboxes_and_signatures():
    app = _app([])
    assert "Yes" in app.field_allowed_values(_field("Approved", "CheckBox"))
    sig = app.field_allowed_values(_field("Sign_Here", "Signature"))
    assert "leave blank" in sig.lower()


def test_export_columns_reuse_explicit_mappings():
    """A teacher's Tab 2 mapping must survive into the sheet they're handed."""
    f = _field("Name")
    f.excel_column = "Preferred Name"
    app = _app([f])
    cols = app.assign_export_columns()
    assert cols == ["Preferred Name"]


def test_export_columns_are_uniquified():
    """'First_Name' and 'First Name' both smart-guess to 'First Name'.
    Duplicate headers get mangled to 'First Name.1' by pandas on re-import,
    silently unmapping one of the fields."""
    app = _app([_field("First_Name"), _field("First Name")])
    cols = app.assign_export_columns()
    assert len(set(cols)) == 2, f"headers must be unique, got {cols}"
    # And the fields now carry the exact headers, so mapping round-trips.
    assert [f.excel_column for f in app.analyzed_fields] == cols


def test_signature_and_button_get_no_data_column():
    app = _app([_field("Name"), _field("Sign", "Signature"), _field("Print", "Button")])
    cols = app.assign_export_columns()
    assert cols == ["Name"]
    assert app.analyzed_fields[1].excel_column is None
    assert app.analyzed_fields[2].excel_column is None
