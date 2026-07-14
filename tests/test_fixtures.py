"""The fixtures must actually reproduce the broken shapes, or the
regression tests that use them prove nothing."""
import fitz
from pypdf import PdfReader

from tests._form_fixture import build_radio_form, build_paired_choice_form


def test_radio_fixture_has_one_group_with_two_kids(tmp_path):
    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    # button_states() dereferences the widget's owning page; read everything
    # BEFORE closing the doc, or the page weakref is dead → ReferenceError.
    doc = fitz.open(pdf)
    page = doc.load_page(0)
    widgets = list(page.widgets())
    names = [w.field_name for w in widgets]
    types = [w.field_type_string for w in widgets]
    states = [
        [s for s in (w.button_states() or {}).get("normal", []) if s != "Off"]
        for w in widgets
    ]
    doc.close()

    # Two widgets, SAME field name — the shape that produced duplicate fields.
    assert len(widgets) == 2
    assert names == ["Gender", "Gender"]
    assert all(t == "RadioButton" for t in types)
    # Each kid reports ONLY its own on-state.
    assert states == [["Male"], ["Female"]]


def test_radio_fixture_is_fillable_by_pypdf(tmp_path):
    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)
    fields = PdfReader(pdf).get_fields()
    assert "Gender" in fields
    assert str(fields["Gender"]["/FT"]) == "/Btn"


def test_paired_choice_fixture_returns_tuples(tmp_path):
    pdf = str(tmp_path / "paired.pdf")
    build_paired_choice_form(pdf)

    doc = fitz.open(pdf)
    widget = next(iter(doc.load_page(0).widgets()))
    values = widget.choice_values
    doc.close()

    # PyMuPDF hands back (export, display) TUPLES — not strings.
    assert values == [("VIC", "Victoria"), ("NSW", "New South Wales")]
