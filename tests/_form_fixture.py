# tests/_form_fixture.py
"""Authors a PDF with one of each common fillable field type.

Used by analyzer and end-to-end fill tests. Radio buttons are intentionally
omitted — PyMuPDF cannot author a radio group (needs a pre-existing
parent/kids structure). Radio handling shares the checkbox code path and is
covered by unit tests on normalize_button_value.
"""
import fitz


def build_mixed_form(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)

    w = fitz.Widget()
    w.field_name = "Student_Name"
    w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w.rect = fitz.Rect(150, 45, 350, 65)
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "Approved"
    w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    w.rect = fitz.Rect(150, 95, 170, 115)
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "State"
    w.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = fitz.Rect(150, 145, 300, 165)
    w.choice_values = ["VIC", "NSW", "QLD", "WA"]
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "Subject"
    w.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
    w.rect = fitz.Rect(150, 195, 300, 265)
    w.choice_values = ["Maths", "English", "Science"]
    page.add_widget(w)

    doc.save(path)
    doc.close()
