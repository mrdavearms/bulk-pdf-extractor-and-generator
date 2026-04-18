"""Generation-path performance regression tests (C3).

Structural tests via inspect.getsource — mirrors the pattern in
tests/test_performance.py rather than relying on flaky timing.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestReaderHoistedOutOfLoop(unittest.TestCase):
    """PdfReader(ctx['pdf_path']) must NOT appear inside _generate_single_pdf."""

    def test_single_pdf_does_not_reopen_reader(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._generate_single_pdf)
        self.assertNotIn(
            "PdfReader(", source,
            "_generate_single_pdf must not call PdfReader() — the reader "
            "should be opened once in run_generation_tab3 and passed in via "
            "ctx. Opening it per-student is a 10–50x generation slowdown."
        )

    def test_run_generation_opens_reader_once(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn(
            "PdfReader(", source,
            "run_generation_tab3 must open the PdfReader once before the "
            "per-student loop."
        )
