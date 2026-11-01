"""Regression tests for the November 2026 dependency and safety audit."""
import inspect
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_gui_audit_fixes import _generate_headless
from tests.test_update_check import REPO, _mock_response, _http_404, _mock_redirect


def _form(tmp):
    from tests._form_fixture import build_mixed_form
    from pdf_analyzer import PDFAnalyzer
    pdf = os.path.join(tmp, "form.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    for f in fields:
        f.excel_column = f.field_name
    return pdf, fields


class TestNoStudentDataInAppLog(unittest.TestCase):
    """app.log is sent with bug reports and often sits in a synced folder."""

    def test_generation_logs_row_numbers_not_names_or_values(self):
        from pdf_generator import BulkPDFGenerator
        src = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        for call in re.findall(r"self\.logger\.\w+\((.*?)\)\n", src, re.S):
            for leak in ("detail", "row_label", "name_parts", "err_str", "str(e)"):
                self.assertNotIn(leak, call, f"logger call passes {leak}: {call}")


class TestOutputPdfWrittenAtomically(unittest.TestCase):
    """A failed write must not leave a truncated PDF that looks finished."""

    def test_failed_write_leaves_no_file_behind(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as tmp:
            pdf, fields = _form(tmp)
            out = os.path.join(tmp, "Jane_Form.pdf")

            def half_write(self, stream):
                stream.write(b"%PDF-1.7 truncated")
                raise OSError("disk full")

            with patch.object(PdfWriter, "write", half_write):
                with self.assertRaises(OSError):
                    _generate_headless(pdf, out, fields, {"Student_Name": "Jane"})
            self.assertFalse(os.path.exists(out))
            self.assertFalse(os.path.exists(out + ".part"))

    def test_successful_write_leaves_only_the_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf, fields = _form(tmp)
            out = os.path.join(tmp, "Jane_Form.pdf")
            _generate_headless(pdf, out, fields, {"Student_Name": "Jane"})
            self.assertTrue(os.path.exists(out))
            self.assertFalse(os.path.exists(out + ".part"))


class TestOutputFilenameLength(unittest.TestCase):

    def test_filename_stem_is_capped(self):
        from pdf_generator import BulkPDFGenerator
        src = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn("stem[:120]", src)


class TestUpdateLinkStaysOnThisRepo(unittest.TestCase):
    """The Download button passes html_url to webbrowser.open."""

    def _check_with_manifest_url(self, html_url):
        import json
        import pdf_generator
        resp = _mock_response("v9.9")
        resp.read.return_value = json.dumps(
            {"version": "v9.9", "html_url": html_url}).encode()
        with patch("urllib.request.urlopen", return_value=resp):
            return pdf_generator.check_for_update("v2.0")

    def test_foreign_manifest_url_is_replaced(self):
        for bad in ("file:///C:/Windows/System32/calc.exe", r"\\server\share\x.exe",
                    "https://evil.example/releases", "https://github.com/someone-else/x"):
            result = self._check_with_manifest_url(bad)
            self.assertEqual(result["status"], "update_available")
            self.assertEqual(result["html_url"], f"{REPO}/releases/latest", bad)

    def test_genuine_manifest_url_is_kept(self):
        good = f"{REPO}/releases/tag/v9.9"
        self.assertEqual(self._check_with_manifest_url(good)["html_url"], good)

    def test_genuine_redirect_url_is_kept(self):
        import pdf_generator
        with patch("urllib.request.urlopen",
                   side_effect=[_http_404(), _mock_redirect("v9.9")]):
            result = pdf_generator.check_for_update("v2.0")
        self.assertEqual(result["html_url"], f"{REPO}/releases/tag/v9.9")


class TestPreviewCacheTracksFileChanges(unittest.TestCase):
    """A revised form saved over last year's file must not show the old page."""

    def test_replaced_pdf_is_rendered_afresh(self):
        from visual_preview import VisualPreviewGenerator
        with tempfile.TemporaryDirectory() as tmp:
            pdf, _ = _form(tmp)
            cache = os.path.join(tmp, "cache")
            with VisualPreviewGenerator(pdf, cache_dir=cache) as vp:
                vp._get_page_image(1, 50)
            first = set(os.listdir(cache))

            # Same path, different content and modified time.
            with open(pdf, "ab") as f:
                f.write(b"\n% revised\n")
            os.utime(pdf, (time.time() + 60, time.time() + 60))
            with VisualPreviewGenerator(pdf, cache_dir=cache) as vp:
                vp._get_page_image(1, 50)
            self.assertEqual(len(set(os.listdir(cache)) - first), 1)

    def test_damaged_cache_file_is_re_rendered(self):
        from visual_preview import VisualPreviewGenerator
        with tempfile.TemporaryDirectory() as tmp:
            pdf, _ = _form(tmp)
            cache = os.path.join(tmp, "cache")
            with VisualPreviewGenerator(pdf, cache_dir=cache) as vp:
                vp._get_page_image(1, 50)
            png = os.path.join(cache, os.listdir(cache)[0])
            with open(png, "wb") as f:
                f.write(b"not a png")
            with VisualPreviewGenerator(pdf, cache_dir=cache) as vp:
                img = vp._get_page_image(1, 50)
            self.assertGreater(img.width, 0)


if __name__ == "__main__":
    unittest.main()
