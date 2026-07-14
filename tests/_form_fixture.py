# tests/_form_fixture.py
"""Authors PDFs with fillable field types, for analyzer and end-to-end fill tests.

build_mixed_form   — text, checkbox, combobox, listbox (via PyMuPDF)
build_radio_form   — a real radio group (hand-written PDF; PyMuPDF's
                     add_widget cannot author the parent/kids structure)
build_paired_choice_form — dropdown with (export, display) option pairs
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


def build_radio_form(path: str) -> None:
    """Author a PDF containing a real radio-button group.

    PyMuPDF's add_widget() cannot create a radio group (it needs a
    pre-existing parent/kids structure), so the PDF bytes are written directly.
    The group 'Gender' has two kid widgets whose on-states are 'Male' and
    'Female' — the shape that broke analysis: every kid reports the *group*
    field name but only its *own* export value from button_states().
    """
    objs = {
        1: "<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [ 6 0 R ] "
           "/DA (/Helv 0 Tf 0 g) >> >>",
        2: "<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>",
        3: "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
           "/Resources << /Font << /Helv 5 0 R >> >> /Contents 4 0 R "
           "/Annots [ 7 0 R 8 0 R ] >>",
        5: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        # /Ff 32768 = bit 16 (Radio)
        6: "<< /FT /Btn /Ff 32768 /T (Gender) /V /Off /Kids [ 7 0 R 8 0 R ] >>",
        7: "<< /Type /Annot /Subtype /Widget /Parent 6 0 R /Rect [50 120 70 140] "
           "/F 4 /AS /Off /AP << /N << /Male 9 0 R /Off 10 0 R >> >> >>",
        8: "<< /Type /Annot /Subtype /Widget /Parent 6 0 R /Rect [50 80 70 100] "
           "/F 4 /AS /Off /AP << /N << /Female 9 0 R /Off 10 0 R >> >> >>",
    }

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}

    def add(num, body):
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj\n{body}\nendobj\n".encode("latin-1"))

    def add_stream(num, dict_extra, stream: bytes):
        offsets[num] = len(out)
        out.extend(
            f"{num} 0 obj\n<< {dict_extra} /Length {len(stream)} >>\nstream\n".encode("latin-1")
        )
        out.extend(stream)
        out.extend(b"\nendstream\nendobj\n")

    for n in (1, 2, 3):
        add(n, objs[n])
    add_stream(4, "", b"BT /Helv 10 Tf 50 160 Td (Gender) Tj ET")
    for n in (5, 6, 7, 8):
        add(n, objs[n])
    add_stream(9, "/Type /XObject /Subtype /Form /BBox [0 0 20 20]",
               b"q 0 0 0 rg 5 5 10 10 re f Q")   # "on" appearance
    add_stream(10, "/Type /XObject /Subtype /Form /BBox [0 0 20 20]",
               b"q 1 1 1 rg 0 0 20 20 re f Q")   # "off" appearance

    xref_pos = len(out)
    max_num = 10
    out.extend(f"xref\n0 {max_num + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for n in range(1, max_num + 1):
        out.extend(f"{offsets[n]:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer\n<< /Size {max_num + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    with open(path, "wb") as f:
        f.write(bytes(out))


def build_paired_choice_form(path: str) -> None:
    """Author a PDF with a dropdown whose /Opt holds (export, display) pairs.

    Government forms routinely do this — display 'Victoria', export 'VIC'.
    PyMuPDF then returns choice_values as a list of TUPLES, which crashed
    field analysis before the flattening fix.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)

    w = fitz.Widget()
    w.field_name = "State"
    w.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = fitz.Rect(50, 50, 250, 70)
    w.choice_values = ["VIC", "NSW"]
    annot = page.add_widget(w)

    doc.xref_set_key(
        annot.xref, "Opt",
        "[ [ (VIC) (Victoria) ] [ (NSW) (New South Wales) ] ]",
    )
    doc.save(path)
    doc.close()
