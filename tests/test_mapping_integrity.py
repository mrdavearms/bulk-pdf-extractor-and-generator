"""Re-loading a corrected spreadsheet is the single most common action a
teacher takes. It must not silently rewrite their field mappings."""
import inspect

import pandas as pd

from models import PDFField
from pdf_generator import BulkPDFGenerator


def _field(name, excel_column=None):
    return PDFField(
        field_name=name, field_type="Text", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 10, 10),
        excel_column=excel_column,
    )


def test_auto_map_preserves_an_explicit_mapping():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name", "Preferred Name"])
    app.analyzed_fields = [_field("Name", excel_column="Preferred Name")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields()

    assert app.analyzed_fields[0].excel_column == "Preferred Name", \
        "a mapping the teacher set by hand must survive a data reload"


def test_auto_map_still_fills_unmapped_fields():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name"])
    app.analyzed_fields = [_field("Name")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields()

    assert app.analyzed_fields[0].excel_column == "Name"


def test_auto_map_can_still_overwrite_when_explicitly_asked():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name"])
    app.analyzed_fields = [_field("Name", excel_column="Something Else")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields(overwrite=True)

    assert app.analyzed_fields[0].excel_column == "Name"


def test_sheet_picker_prefers_the_data_entry_sheet():
    """The app's own workbook lists 'Field Mapping' first. Defaulting to
    sheet 0 loaded the reference sheet as data."""
    src = inspect.getsource(BulkPDFGenerator._pick_excel_sheet)
    assert "Data Entry" in src, "picker must prefer the Data Entry sheet"
    assert "combo.current(0)" not in src, "picker must not hard-default to sheet 0"
