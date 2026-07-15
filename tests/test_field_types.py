from models import PDFField
import inspect
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _form_fixture import build_mixed_form
from pdf_analyzer import PDFAnalyzer
from pypdf.generic import NameObject
from field_values import normalize_button_value, normalize_choice_value
import pandas as pd
from pypdf import PdfReader
import fitz
from pdf_generator import BulkPDFGenerator, _field_type_detail


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


def test_blank_and_nan_cells_leave_fields_untouched(tmp_path):
    pdf = str(tmp_path / "form.pdf"); out = str(tmp_path / "out.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    warns = _generate(pdf, out, fields, {
        "Student_Name": "Jane",
        "Approved": float("nan"),   # blank checkbox cell
        "State": float("nan"),      # blank dropdown cell
        "Subject": "",              # blank listbox cell
    })
    # Blank/NaN cells must not produce spurious "nan" warnings...
    assert all("nan" not in w.lower() for w in warns)
    doc = fitz.open(out)
    vals = {w.field_name: w.field_value for w in doc[0].widgets()}
    doc.close()
    # ...and must not write literal "nan" into any field.
    assert vals["Approved"] in (None, "Off", False)
    assert "nan" not in str(vals["State"]).lower()
    assert vals["Student_Name"] == "Jane"


def test_field_type_detail_shows_choice_options():
    f = _make(field_type="ComboBox", options=["VIC", "NSW", "QLD", "WA"])
    detail = _field_type_detail(f)
    assert detail.startswith("ComboBox")
    assert "VIC" in detail and "NSW" in detail


def test_field_type_detail_truncates_many_options():
    f = _make(field_type="ListBox", options=["a", "b", "c", "d", "e", "f"])
    detail = _field_type_detail(f)
    assert "…" in detail  # ellipsis when more than 4 options


def test_field_type_detail_shows_tick_hint_for_checkbox():
    f = _make(field_type="CheckBox", on_states=["Yes"])
    detail = _field_type_detail(f)
    assert detail.startswith("CheckBox")
    assert "tick" in detail.lower()


def test_field_type_detail_plain_for_text():
    f = _make(field_type="Signature")
    assert _field_type_detail(f) == "Signature"


def test_paired_option_dropdown_analyses_to_export_values(tmp_path):
    """A dropdown with (export, display) pairs must analyse to flat export
    strings. Before the fix, PyMuPDF's tuples reached PDFField.options and
    blew up the audit dialog's ", ".join(...) — killing the whole analysis."""
    from tests._form_fixture import build_paired_choice_form

    pdf = str(tmp_path / "paired.pdf")
    build_paired_choice_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    state = next(f for f in fields if f.field_name == "State")
    assert state.options == ["VIC", "NSW"]
    assert all(isinstance(o, str) for o in state.options)
    # The audit dialog does exactly this — it must not raise.
    assert ", ".join(state.options) == "VIC, NSW"


def test_radio_group_becomes_one_field_with_all_on_states(tmp_path):
    """A radio group must analyse to ONE field carrying EVERY option.

    Before the fix: two 'Gender' fields, each with on_states=['Male'] or
    ['Female']. len(on_states)<=1 meant normalize_button_value applied
    checkbox semantics — typing 'Male' filled nothing, typing 'Yes' let an
    arbitrary option win."""
    from tests._form_fixture import build_radio_form

    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    genders = [f for f in fields if f.field_name == "Gender"]
    assert len(genders) == 1, "radio group must not fan out into one field per button"
    assert genders[0].field_type == "RadioButton"
    assert sorted(genders[0].on_states) == ["Female", "Male"]


def test_radio_group_fills_the_chosen_option_end_to_end(tmp_path):
    """The whole point: a teacher types 'Female' and that button is selected."""
    from pypdf import PdfReader
    from tests._form_fixture import build_radio_form
    from field_values import normalize_button_value

    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        field = next(f for f in analyzer.analyze_fields() if f.field_name == "Gender")

    name_val = normalize_button_value("Female", field.on_states)
    assert name_val is not None, "'Female' must resolve against the group's on-states"

    from pypdf import PdfWriter
    out = str(tmp_path / "filled.pdf")
    writer = PdfWriter(clone_from=pdf)
    for page in writer.pages:
        writer.update_page_form_field_values(
            page, {"Gender": name_val}, auto_regenerate=True)
    with open(out, "wb") as fh:
        writer.write(fh)

    assert str(PdfReader(out).get_fields()["Gender"]["/V"]) == "/Female"


def test_same_field_on_two_pages_yields_one_field(tmp_path):
    """A field whose widget repeats on several pages produced duplicate rows,
    duplicate spreadsheet columns, and a header pandas mangles to 'Name.1'."""
    import fitz

    pdf = str(tmp_path / "twopage.pdf")
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=300, height=200)
        w = fitz.Widget()
        w.field_name = "Student_Name"
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(50, 50, 250, 70)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    assert [f.field_name for f in fields].count("Student_Name") == 1


def test_numbered_checkbox_row_is_not_merged_into_a_comb(tmp_path):
    """Checkboxes named Q1_1..Q1_4 on one line satisfy the comb heuristics by
    name and geometry. Merging them would write one CHARACTER per checkbox —
    they never tick, and the value is destroyed."""
    import fitz

    pdf = str(tmp_path / "checkrow.pdf")
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    for i in range(1, 5):
        w = fitz.Widget()
        w.field_name = f"Q1_{i}"
        w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        w.rect = fitz.Rect(50 + i * 30, 100, 70 + i * 30, 120)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    assert not any(f.is_combed for f in fields)
    assert sorted(f.field_name for f in fields) == ["Q1_1", "Q1_2", "Q1_3", "Q1_4"]
    assert all(f.field_type == "CheckBox" for f in fields)


def test_checkbox_on_a_non_final_page_analyses(tmp_path):
    """Pre-existing crash: analyze_fields collected every widget and read
    button_states() lazily, after the owning page had been GC'd — raising
    ReferenceError on ANY multi-page PDF with a checkbox/radio not on the last
    page. That is the shape of a real VCAA exam form."""
    import fitz

    pdf = str(tmp_path / "multipage.pdf")
    doc = fitz.open()
    for pg in range(4):
        page = doc.new_page(width=300, height=200)
        if pg == 0:   # checkbox on the FIRST of four pages
            w = fitz.Widget()
            w.field_name = "Approved"
            w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = fitz.Rect(50, 50, 70, 70)
            page.add_widget(w)
    doc.save(pdf)
    doc.close()

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()   # must not raise ReferenceError

    approved = [f for f in fields if f.field_name == "Approved"]
    assert len(approved) == 1
    assert approved[0].field_type == "CheckBox"
    assert approved[0].page == 1


def test_push_button_is_never_filled():
    """A 'Print Form' push button is not a data field. Writing a value into
    it can corrupt its appearance state — skip it like a signature."""
    from pdf_generator import BulkPDFGenerator

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    src = inspect.getsource(app._generate_single_pdf)
    assert "'Button'" in src or '"Button"' in src, \
        "_generate_single_pdf must explicitly skip push-button fields"


def test_comb_truncation_produces_a_warning(tmp_path):
    """Silent truncation is data loss. The teacher must be told."""
    import pandas as pd
    from pypdf import PdfReader
    from pdf_generator import BulkPDFGenerator
    from models import PDFField

    # A 5-box comb field, given a 9-character value.
    field = PDFField(
        field_name="Surname",
        field_type="Text-Combed",
        page=1,
        length=5,
        is_combed=True,
        combed_fields=[f"Surname[{i}]" for i in range(5)],
        rect=(0, 0, 10, 10),
        excel_column="Surname",
    )

    pdf = str(tmp_path / "comb.pdf")
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=300, height=200)
    for i in range(5):
        w = fitz.Widget()
        w.field_name = f"Surname[{i}]"
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(20 + i * 20, 50, 38 + i * 20, 70)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    reader = PdfReader(pdf)
    ctx = {
        '_reader': reader,
        'analyzed_fields': [field],
        'pdf_fields': [],
        'combed_padding': False,
        'combed_align': 'left',
    }
    row = pd.Series({"Surname": "Nguyenson"})   # 9 chars into 5 boxes
    warnings = app._generate_single_pdf(ctx, row, str(tmp_path / "out.pdf"))
    reader.close()

    assert warnings, "truncation must produce a warning"
    joined = " ".join(warnings)
    assert "Surname" in joined
    assert "Nguye" in joined      # what actually got written


def test_non_ascii_names_survive_a_fill(tmp_path):
    """Vietnamese/Chinese names are routine in Victorian schools."""
    import pandas as pd
    from pypdf import PdfReader
    from pdf_generator import BulkPDFGenerator
    from models import PDFField
    from tests._form_fixture import build_mixed_form

    pdf = str(tmp_path / "form.pdf")
    build_mixed_form(pdf)

    field = PDFField(
        field_name="Student_Name", field_type="Text", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 10, 10),
        excel_column="Student_Name",
    )

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    reader = PdfReader(pdf)
    ctx = {
        '_reader': reader,
        'analyzed_fields': [field],
        'pdf_fields': [],
        'combed_padding': False,
        'combed_align': 'left',
    }
    out = str(tmp_path / "out.pdf")
    app._generate_single_pdf(ctx, pd.Series({"Student_Name": "Nguyễn Thị Hương"}), out)
    reader.close()

    assert PdfReader(out).get_fields()["Student_Name"]["/V"] == "Nguyễn Thị Hương"
