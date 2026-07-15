"""A student who is missing one field must still appear in the preview — with
a warning. Dropping the row hides them from selection entirely."""
import inspect

import numpy as np
import pandas as pd

from pdf_generator import BulkPDFGenerator


def test_row_is_blank_only_when_every_cell_is_empty():
    assert BulkPDFGenerator.row_is_blank(pd.Series({"a": "", "b": np.nan}))
    assert BulkPDFGenerator.row_is_blank(pd.Series({"a": "   ", "b": None}))
    # A student with no surname is NOT a blank row.
    assert not BulkPDFGenerator.row_is_blank(pd.Series({"Surname": "", "DOB": "1/1/2010"}))


def test_preview_does_not_skip_on_the_first_column_alone():
    src = inspect.getsource(BulkPDFGenerator.show_preview_tab3)
    assert "row_is_blank" in src, \
        "preview must skip only fully-blank rows, not rows missing their first value"
    assert "if self._preview_columns and not first_val" not in src, \
        "the first-column skip drops students who are missing that one field"


def test_validation_uses_the_same_blank_rule_as_the_preview():
    """Otherwise validation shouts about 70 bad records while the table shows 30."""
    src = inspect.getsource(BulkPDFGenerator.validate_data_tab3)
    assert "row_is_blank" in src
