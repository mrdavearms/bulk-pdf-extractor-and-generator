"""Regression tests for the September 2026 GUI audit fixes.

GUI behaviour is checked structurally via inspect.getsource (headless CI has
no display — see CLAUDE.md); value handling is tested directly.
"""
import inspect
import os
import re
import unittest


class TestSplitDatePartsAreNotDates(unittest.TestCase):
    """The VCAA form splits DOB into 'day of birth' / 'DOB month' / 'dob year'.
    Typing those as Date ran 21 / 4 / 2008 through the Excel-serial converter
    and wrote 20 / 03 / 30/0 into the birth-date boxes."""

    def test_date_part_fields_default_to_text(self):
        from pdf_generator import _guess_data_type
        for name in ["day of birth", "DOB month", "dob year", "Birth Year",
                     "Date_of_Birth_Day", "Expiry month"]:
            self.assertEqual(_guess_data_type(name), "text", name)

    def test_whole_date_fields_still_default_to_date(self):
        from pdf_generator import _guess_data_type
        for name in ["Date of Birth", "DOB", "Date implemented 1",
                     "Birthdate", "Expiry Date", "Due Date"]:
            self.assertEqual(_guess_data_type(name), "date", name)


class TestSmallNumbersAreNotExcelSerials(unittest.TestCase):
    """A day, month or year typed into a Date-typed box must pass through
    untouched; only realistic serials (>= 10000, i.e. from 1927) convert."""

    def setUp(self):
        from pdf_generator import BulkPDFGenerator
        self.fmt = BulkPDFGenerator.format_value_tab3

    def test_day_month_year_pass_through(self):
        self.assertEqual(self.fmt('21', data_type='date'), '21')
        self.assertEqual(self.fmt(21, data_type='date'), '21')
        self.assertEqual(self.fmt('4', data_type='date'), '4')
        self.assertEqual(self.fmt('2008', data_type='date'), '2008')
        self.assertEqual(self.fmt(2008.0, data_type='date'), '2008.0')

    def test_real_serials_still_convert(self):
        self.assertEqual(self.fmt('45313', data_type='date'), '22/01/2024')
        self.assertEqual(self.fmt(45313, data_type='date'), '22/01/2024')
        self.assertEqual(self.fmt(45313.0, data_type='date'), '22/01/2024')
        self.assertEqual(self.fmt('10000', data_type='date'), '18/05/1927')

    def test_iso_datetime_strings_still_convert(self):
        self.assertEqual(self.fmt('2026-02-10 00:00:00', data_type='date'), '10/02/2026')


class TestWindowsCsvEncoding(unittest.TestCase):
    """Excel on Windows writes cp1252, not latin-1. The latin-1 fallback turned
    O’Brien into O\\x92Brien in the preview, the PDF and the filename."""

    def test_csv_fallback_is_cp1252_everywhere(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.load_data_tab3)
        self.assertNotIn("encoding='latin-1'", source)
        self.assertNotIn("encoding='latin1'", source)
        self.assertEqual(source.count("encoding='cp1252'"), 2,
                         "both the data read and the raw-header re-read need the fallback")


class TestSamePath(unittest.TestCase):
    def test_same_path_tolerates_relative_and_case(self):
        from pdf_generator import _same_path
        here = os.path.abspath(__file__)
        self.assertTrue(_same_path(here, os.path.relpath(here)))
        self.assertFalse(_same_path(here, here + ".bak"))
        self.assertFalse(_same_path(None, here))
        self.assertFalse(_same_path("", ""))


class TestTemplateDoesNotBleedOntoAnotherPdf(unittest.TestCase):
    """A saved template's combed lengths, data types and column mappings must
    only be applied to the PDF it was saved from."""

    def test_analyze_drops_template_for_a_different_pdf(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.analyze_pdf_fields)
        self.assertIn("_same_path(self.current_template.pdf_path", source)
        self.assertIn("self.current_template = None", source)

    def test_template_load_reanalyses_when_fields_are_for_another_pdf(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.load_template_config)
        self.assertIn("_same_path(self._analyzed_pdf_path", source)
        self.assertIn("self._analyzed_pdf_path = pdf_path", source)


class TestTemplateLoadWithMissingPdf(unittest.TestCase):
    def test_missing_pdf_is_an_error_not_a_success(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.load_template_config)
        check = source.index("os.path.exists(pdf_path)")
        success = source.index('messagebox.showinfo("Template Loaded"')
        self.assertLess(check, success, "existence check must run before the success message")
        self.assertIn("showerror", source[check:success])
        # the failed load must not leave a half-set current_template behind
        self.assertLess(check, source.index("self.current_template = template"))


class TestOutputFilenameUsesTemplateName(unittest.TestCase):
    def test_ctx_template_name_comes_from_tab1_name(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.start_generation_tab3)
        self.assertIn("self.template_name_var.get()", source)


class TestScrollableFrameFollowsWindowWidth(unittest.TestCase):
    """Content sat at its natural width, pushing Tab 3's Browse buttons past
    the right edge of a 1000px window with no horizontal scrollbar."""

    def test_canvas_configure_resizes_the_embedded_frame(self):
        from pdf_generator import ScrollableFrame
        source = inspect.getsource(ScrollableFrame.__init__)
        self.assertIn('"<Configure>", self._on_canvas_configure', source)
        fit = inspect.getsource(ScrollableFrame._fit_content_width)
        self.assertIn("itemconfigure", fit)
        self.assertIn("winfo_reqwidth", fit, "never narrower than the content needs")

    def test_tab3_status_text_is_not_on_the_template_row(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.setup_tab3_generate)
        self.assertIn("self.matching_status_label = ttk.Label(container,", source)


class TestMouseWheelWorksOverContent(unittest.TestCase):
    """The wheel was bound on the canvas only; over a label, button, entry or
    table the page did not scroll."""

    def test_dispatcher_uses_pointer_position(self):
        from pdf_generator import ScrollableFrame
        source = inspect.getsource(ScrollableFrame._dispatch_mousewheel)
        self.assertIn("winfo_containing(event.x_root, event.y_root)", source)
        self.assertIn("isinstance(w, ScrollableFrame)", source)
        # nested scrollers keep the wheel
        self.assertIn("'Treeview'", source)

    def test_binding_is_global_not_per_canvas(self):
        from pdf_generator import ScrollableFrame
        source = inspect.getsource(ScrollableFrame._install_wheel_dispatcher)
        self.assertIn("bind_all", source)
        init = inspect.getsource(ScrollableFrame.__init__)
        self.assertNotIn('"<Enter>"', init)


class TestPrimaryActionsArePinned(unittest.TestCase):
    """Save Template and Generate sat 400px+ below the fold of the default
    window (and further on a 1366x768 laptop)."""

    def test_pages_have_action_bars(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.setup_ui)
        self.assertIn("_make_page_with_action_bar()", source)
        bar = inspect.getsource(BulkPDFGenerator._make_page_with_action_bar)
        self.assertIn("side=tk.BOTTOM", bar)

    def test_generate_button_lives_in_the_bar(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.setup_tab3_generate)
        self.assertIn("self.generate_btn_tab3 = ttk.Button(\n            self.tab3_actions,", source)
        self.assertIn("self.results_frame_tab3 = tk.Frame(self.tab3_actions", source)

    def test_save_template_lives_in_the_bar(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.setup_tab1_analyze)
        self.assertIn("action_frame = tk.Frame(self.tab1_actions", source)


# ── "smaller things" from the same audit ─────────────────────────────────────

def _generate_headless(pdf_path, out_path, fields, row_values):
    import pandas as pd
    from pypdf import PdfReader
    from pdf_generator import BulkPDFGenerator
    ctx = {"analyzed_fields": fields, "combed_padding": False, "combed_align": "left",
           "pdf_fields": [f.field_name for f in fields], "_reader": PdfReader(pdf_path)}
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    try:
        return app._generate_single_pdf(ctx, pd.Series(row_values), out_path)
    finally:
        ctx["_reader"].close()


class TestUnmappedFieldsAreLeftBlank(unittest.TestCase):
    """'-- not mapped --' and Clear All Mappings used to be cosmetic: generation
    fell back to matching by field name and filled the field anyway."""

    def _fields(self, tmp):
        from tests._form_fixture import build_mixed_form
        from pdf_analyzer import PDFAnalyzer
        pdf = os.path.join(tmp, "form.pdf")
        build_mixed_form(pdf)
        with PDFAnalyzer(pdf) as az:
            return pdf, az.analyze_fields()

    def test_cleared_mapping_is_not_filled_even_when_the_column_name_matches(self):
        import tempfile, fitz
        with tempfile.TemporaryDirectory() as tmp:
            pdf, fields = self._fields(tmp)
            for f in fields:
                f.excel_column = None if f.field_name == "Student_Name" else f.field_name
            out = os.path.join(tmp, "out.pdf")
            _generate_headless(pdf, out, fields, {"Student_Name": "Jane", "State": "NSW",
                                                  "Subject": "English", "Approved": "X"})
            doc = fitz.open(out)
            vals = {w.field_name: w.field_value for w in doc[0].widgets()}
            doc.close()
            self.assertIn(vals["Student_Name"], ("", None))
            self.assertEqual(vals["State"], "NSW")

    def test_a_pdf_nothing_reached_is_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pdf, fields = self._fields(tmp)
            for f in fields:
                f.excel_column = None
            warns = _generate_headless(pdf, os.path.join(tmp, "out.pdf"), fields,
                                       {"Student_Name": "Jane"})
            self.assertTrue(any("blank" in w for w in warns), warns)

    def test_no_by_name_fallback_remains_in_generation(self):
        from pdf_generator import BulkPDFGenerator
        for meth in (BulkPDFGenerator._generate_single_pdf, BulkPDFGenerator.run_generation_tab3,
                     BulkPDFGenerator.validate_data_tab3, BulkPDFGenerator.show_preview_tab3):
            self.assertIsNone(re.search(r"excel_column or \w+\.field_name", inspect.getsource(meth)),
                              meth.__name__)

    def test_auto_map_runs_before_validation_on_load(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.load_data_tab3)
        self.assertLess(source.index("self._auto_map_fields()"),
                        source.index("self.validate_data_tab3()"))
        self.assertIn("self._auto_map_fields()",
                      inspect.getsource(BulkPDFGenerator.load_template_config))


class TestBlankIdentifiersAreReported(unittest.TestCase):
    """A row with no surname/first name generated 'cleanly' as Row_1.pdf."""

    def test_generation_flags_rows_with_blank_critical_fields(self):
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn("blank_critical", source)
        self.assertIn("no value for", source)


class TestDeadSettingsRemoved(unittest.TestCase):
    def test_unused_keys_are_gone_but_old_files_still_load(self):
        import dataclasses
        from models import AppSettings
        names = {f.name for f in dataclasses.fields(AppSettings)}
        self.assertNotIn("auto_load_last_template", names)
        self.assertNotIn("last_template", names)
        old = ('{"templates_directory": "/x", "auto_load_last_template": true, '
               '"last_template": null, "school_name": "WHS"}')
        s = AppSettings.from_json(old)
        self.assertEqual(s.school_name, "WHS")


if __name__ == "__main__":
    unittest.main()
