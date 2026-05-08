"""Fidelity tests — prove silent-data-corruption bugs stay fixed.

These tests live at the data boundary: what the user put in the spreadsheet
must be what ends up in the PDF. No silent coercion, no lost leading zeros,
no lost dates.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


class TestCsvLeadingZeroPreservation(unittest.TestCase):
    """CSV load must use dtype=str so leading-zero IDs survive (C1)."""

    def test_csv_load_matches_excel_dtype_str(self):
        """The CSV branch of load_data_tab3 must pass dtype=str to pd.read_csv."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.load_data_tab3)
        csv_reads = [line for line in source.split('\n') if 'read_csv' in line]
        self.assertTrue(len(csv_reads) >= 1,
                        "Expected at least one pd.read_csv call in load_data_tab3")
        for line in csv_reads:
            self.assertIn('dtype=str', line,
                          f"pd.read_csv must pass dtype=str to preserve leading "
                          f"zeros and prevent date re-formatting: {line.strip()}")

    def test_csv_dtype_str_actually_preserves_leading_zeros(self):
        """Documentation test: confirms the pandas behaviour the fix relies on."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding='utf-8-sig'
        ) as f:
            f.write('Student ID,Name\n')
            f.write('00123,Smith\n')
            f.write('00045,Jones\n')
            path = f.name
        self.addCleanup(os.unlink, path)

        # Without dtype=str — leading zeros would be lost (inferred as int64)
        df_numeric = pd.read_csv(path, encoding='utf-8-sig')
        self.assertEqual(df_numeric.iloc[0]['Student ID'], 123,
                         "Baseline: without dtype=str pandas coerces to int")

        # With dtype=str — what the fix applies
        df_str = pd.read_csv(path, dtype=str, encoding='utf-8-sig')
        self.assertEqual(df_str.iloc[0]['Student ID'], '00123',
                         "dtype=str must preserve the literal string '00123'")
        self.assertEqual(df_str.iloc[1]['Student ID'], '00045')


class TestPdfReaderClosedInLoadData(unittest.TestCase):
    """load_data_tab3 must close the PdfReader so Windows releases the file lock.

    Without this, the template PDF stays "in use" until the app exits, blocking
    teachers from opening the same template in Adobe or renaming/moving the file.
    Mirrors the v2.11 fix in run_generation_tab3 (C3 / 8d09e81).
    """

    def test_load_data_closes_reader_in_finally(self):
        """The PdfReader opened in load_data_tab3 must be closed in a finally block."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.load_data_tab3)

        self.assertIn('PdfReader(', source,
                      "load_data_tab3 should still open a PdfReader")
        self.assertIn('reader.close()', source,
                      "load_data_tab3 must explicitly close the PdfReader to "
                      "release the Windows file lock — without this the "
                      "template PDF stays in use until the app exits")

        # Walk lines: after `reader = PdfReader(`, the next `try:` must be
        # followed by a `finally:` that contains `reader.close()`. This guards
        # against a future refactor that drops the close into the happy path.
        lines = source.split('\n')
        opened_at = next(
            (i for i, ln in enumerate(lines) if 'PdfReader(' in ln and 'reader' in ln),
            None,
        )
        self.assertIsNotNone(opened_at, "expected a `reader = PdfReader(...)` line")

        tail = '\n'.join(lines[opened_at:])
        try_idx = tail.find('try:')
        finally_idx = tail.find('finally:')
        close_idx = tail.find('reader.close()')
        self.assertTrue(0 <= try_idx < finally_idx < close_idx,
                        "PdfReader must be opened, then `try:` then `finally: "
                        "reader.close()` — current order does not guarantee "
                        "close on the early-return path")


class TestFallbackPathDateConversion(unittest.TestCase):
    """Fallback auto-match path must pass data_type so date fields convert (C2)."""

    def test_fallback_path_passes_data_type(self):
        """The else-branch in _generate_single_pdf must resolve a data_type."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._generate_single_pdf)
        calls = [line.strip() for line in source.split('\n')
                 if 'format_value_tab3' in line and 'def ' not in line]
        self.assertTrue(len(calls) >= 2,
                        "Expected two format_value_tab3 call sites "
                        "(analyzed path + fallback path)")
        for call in calls:
            self.assertIn('data_type', call,
                          f"format_value_tab3 must receive a data_type arg "
                          f"so Excel-serial dates convert in the fallback "
                          f"path: {call}")
        self.assertIn('inferred_type', source,
                      "fallback path must use a variable for data_type "
                      "(e.g. inferred_type), not a hardcoded literal string")
