from models import PDFField
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _form_fixture import build_mixed_form
from pdf_analyzer import PDFAnalyzer
from pypdf.generic import NameObject
from field_values import normalize_button_value, normalize_choice_value
import warnings
import pandas as pd
from pypdf import PdfReader
import fitz
from pdf_generator import BulkPDFGenerator


def _make(**kw):
    base = dict(
        field_name="Approved", field_type="CheckBox", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 1, 1),
    )
    base.update(kw)
    return PDFField(**base)


def test_pdffield_has_button_and_choice_metadata_defaults():
    f = _make()
    assert f.on_states == []
    assert f.options == []


def test_pdffield_roundtrips_button_and_choice_metadata():
    f = _make(field_type="ComboBox", on_states=["Yes"], options=["VIC", "NSW"])
    restored = PDFField.from_dict(f.to_dict())
    assert restored.on_states == ["Yes"]
    assert restored.options == ["VIC", "NSW"]


def test_analysis_captures_button_and_choice_metadata(tmp_path):
    pdf = str(tmp_path / "form.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = {f.field_name: f for f in az.analyze_fields()}

    assert fields["Approved"].field_type == "CheckBox"
    assert "Yes" in fields["Approved"].on_states

    assert fields["State"].field_type == "ComboBox"
    assert fields["State"].options == ["VIC", "NSW", "QLD", "WA"]

    assert fields["Subject"].field_type == "ListBox"
    assert fields["Subject"].options == ["Maths", "English", "Science"]


def test_checkbox_truthy_maps_to_on_state_nameobject():
    assert normalize_button_value("X", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("yes", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("TRUE", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("1", ["Yes"]) == NameObject("/Yes")


def test_checkbox_falsey_maps_to_off():
    assert normalize_button_value("No", ["Yes"]) == NameObject("/Off")
    assert normalize_button_value("0", ["Yes"]) == NameObject("/Off")
    assert normalize_button_value("", ["Yes"]) == NameObject("/Off")


def test_checkbox_unrecognised_returns_none():
    assert normalize_button_value("maybe", ["Yes"]) is None


def test_radio_value_matches_one_of_several_states_case_insensitively():
    assert normalize_button_value("male", ["Male", "Female"]) == NameObject("/Male")
    assert normalize_button_value("FEMALE", ["Male", "Female"]) == NameObject("/Female")
    assert normalize_button_value("other", ["Male", "Female"]) is None


def test_choice_validates_against_options_case_insensitively():
    assert normalize_choice_value("nsw", ["VIC", "NSW"]) == ("NSW", True)
    assert normalize_choice_value(" VIC ", ["VIC", "NSW"]) == ("VIC", True)
    assert normalize_choice_value("Victoria", ["VIC", "NSW"]) == ("Victoria", False)


def test_checkbox_empty_on_states_falls_back_to_yes():
    assert normalize_button_value("yes", []) == NameObject("/Yes")
    assert normalize_button_value("no", []) == NameObject("/Off")


def test_choice_empty_options_returns_raw_unmatched():
    assert normalize_choice_value("Anything", []) == ("Anything", False)


def _generate(pdf_path, out_path, fields, row_values):
    ctx = {
        "analyzed_fields": fields,
        "combed_padding": False,
        "combed_align": "left",
        "pdf_fields": [f.field_name for f in fields],
        "_reader": PdfReader(pdf_path),
    }
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)  # real method, no GUI
    warnings_out = app._generate_single_pdf(ctx, pd.Series(row_values), out_path)
    ctx["_reader"].close()
    return warnings_out


def test_checkbox_fills_with_natural_value(tmp_path):
    pdf = str(tmp_path / "form.pdf"); out = str(tmp_path / "out.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    _generate(pdf, out, fields, {
        "Student_Name": "Jane Smith", "Approved": "X",
        "State": "NSW", "Subject": "English",
    })
    doc = fitz.open(out)
    vals = {w.field_name: w.field_value for w in doc[0].widgets()}
    doc.close()
    assert vals["Approved"] == "Yes"        # ticked, not "Off"
    assert vals["Student_Name"] == "Jane Smith"
    assert vals["State"] == "NSW"
    assert vals["Subject"] == "English"


def test_invalid_choice_value_is_reported(tmp_path):
    pdf = str(tmp_path / "form.pdf"); out = str(tmp_path / "out.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    warns = _generate(pdf, out, fields, {
        "Student_Name": "X", "Approved": "no",
        "State": "Victoria",  # not a valid option
        "Subject": "Maths",
    })
    assert any("State" in w and "Victoria" in w for w in warns)
