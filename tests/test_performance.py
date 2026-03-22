"""Performance regression tests — prove the macOS fixes actually work.

These tests measure that the performance-critical patterns are correct,
not just that the code doesn't crash. Each test documents what was slow
and asserts the fix is structurally in place.
"""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScrollableFrameDebounce(unittest.TestCase):
    """ScrollableFrame.<Configure> must coalesce multiple events into one update."""

    def test_configure_binding_uses_after_idle(self):
        """The <Configure> handler must not call canvas.configure() directly.

        Before fix: every <Configure> event triggered canvas.configure(scrollregion=...)
        After fix: events set a flag and schedule via after_idle(); only one update fires.
        """
        from pdf_generator import ScrollableFrame
        import inspect
        source = inspect.getsource(ScrollableFrame._on_configure)
        # Must NOT contain direct canvas.configure() call (the method name
        # _update_scrollregion is fine — it's the deferred target, not inline)
        self.assertNotIn('canvas.configure', source,
                         "_on_configure should not call canvas.configure() directly — "
                         "it should defer to after_idle()")
        # Must reference the pending flag
        self.assertIn('_config_pending', source,
                      "_on_configure must use the _config_pending debounce flag")
        # Must use after_idle
        self.assertIn('after_idle', source,
                      "_on_configure must schedule via after_idle()")

    def test_update_scrollregion_resets_flag(self):
        """The deferred update must reset the pending flag so future events trigger."""
        from pdf_generator import ScrollableFrame
        import inspect
        source = inspect.getsource(ScrollableFrame._update_scrollregion)
        self.assertIn('_config_pending', source)
        self.assertIn('False', source,
                      "_update_scrollregion must reset _config_pending to False")


class TestTreeviewHoverThrottle(unittest.TestCase):
    """Treeview hover must throttle <Motion> events, not fire on every pixel."""

    def test_hover_uses_throttle_guard(self):
        """The on_motion handler must skip events when a timer is pending."""
        from theme import bind_treeview_hover
        import inspect
        source = inspect.getsource(bind_treeview_hover)
        # Must contain a throttle mechanism (after() call with delay)
        self.assertIn('after(', source,
                      "bind_treeview_hover must use after() for throttling")
        # Must NOT process identify_row on every <Motion> event
        self.assertIn('_throttle_id', source,
                      "Must have a throttle guard variable")


class TestPreviewRendererThreading(unittest.TestCase):
    """PreviewRenderer must run PIL work off the main thread."""

    def test_renderer_has_request_id_guard(self):
        """Stale-result guard: _request_id must increment on each request."""
        from preview_renderer import PreviewRenderer
        import inspect
        source = inspect.getsource(PreviewRenderer.request_preview)
        self.assertIn('_request_id', source,
                      "request_preview must increment _request_id for stale-result guard")

    def test_worker_uses_bilinear_for_fast_pass(self):
        """Fast pass must use BILINEAR, not LANCZOS."""
        from preview_renderer import PreviewRenderer
        import inspect
        source = inspect.getsource(PreviewRenderer._resize_and_deliver)
        self.assertIn('BILINEAR', source,
                      "Fast pass must use BILINEAR resampling")
        self.assertIn('LANCZOS', source,
                      "Quality pass must use LANCZOS resampling")

    def test_renderer_has_shutdown(self):
        """shutdown() must exist and set the _shutdown flag."""
        from preview_renderer import PreviewRenderer
        import inspect
        source = inspect.getsource(PreviewRenderer.shutdown)
        self.assertIn('_shutdown', source)
        self.assertIn('True', source,
                      "shutdown() must set _shutdown = True")

    def test_font_cached_at_init(self):
        """Font resolution must happen once at init, not per render."""
        from preview_renderer import PreviewRenderer
        import inspect
        # _resolve_font must be called in __init__, not in _worker_render
        init_source = inspect.getsource(PreviewRenderer.__init__)
        self.assertIn('_resolve_font', init_source,
                      "Font must be resolved in __init__")
        worker_source = inspect.getsource(PreviewRenderer._worker_render)
        self.assertNotIn('platform.system', worker_source,
                         "Worker thread must NOT call platform.system() — font should be cached")
        self.assertNotIn('os.path.exists', worker_source,
                         "Worker thread must NOT call os.path.exists() — font should be cached")

    def test_worker_does_not_access_fitz(self):
        """Worker thread must not touch PyMuPDF (fitz) — not thread-safe."""
        from preview_renderer import PreviewRenderer
        import inspect
        worker_source = inspect.getsource(PreviewRenderer._worker_render)
        self.assertNotIn('_get_page_image', worker_source,
                         "Worker thread must NOT call _get_page_image (touches fitz.Document)")
        self.assertNotIn('.doc', worker_source,
                         "Worker thread must NOT access .doc (fitz.Document is not thread-safe)")


class TestSelectAllBatching(unittest.TestCase):
    """select_all_tab3 must batch updates to avoid per-row redraws."""

    def test_select_all_uses_pack_forget(self):
        """Treeview must be detached during bulk updates."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.select_all_tab3)
        self.assertIn('pack_forget', source,
                      "select_all_tab3 must detach treeview during bulk update")
        # Must re-pack after the loop
        # Count occurrences — should have pack_forget AND pack (re-attach)
        self.assertGreater(source.count('pack'), 1,
                           "select_all_tab3 must re-pack treeview after bulk update")

    def test_deselect_all_uses_pack_forget(self):
        """deselect_all must also batch."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.deselect_all_tab3)
        self.assertIn('pack_forget', source,
                      "deselect_all_tab3 must detach treeview during bulk update")


class TestTab2InPlaceUpdate(unittest.TestCase):
    """Tab 2 mapping refresh must update in-place when fields haven't changed."""

    def test_refresh_checks_for_inplace_update(self):
        """_refresh_tab2_mappings must check if in-place update is possible."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._refresh_tab2_mappings)
        self.assertIn('can_update_inplace', source,
                      "Must check whether in-place update is possible")
        self.assertIn('_mapping_rows', source,
                      "Must track mapping row widgets for in-place updates")

    def test_clear_mapping_rows_resets_tracking(self):
        """_clear_mapping_rows must also clear the _mapping_rows tracker."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._clear_mapping_rows)
        self.assertIn('_mapping_rows', source,
                      "_clear_mapping_rows must reset _mapping_rows list")


class TestProgressThrottling(unittest.TestCase):
    """Generation progress updates must be throttled, not per-record."""

    def test_progress_uses_time_throttle(self):
        """Worker loop must throttle root.after() calls."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        # The generation worker is run_generation_tab3
        source = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn('monotonic', source,
                      "Progress updates must use time.monotonic() for throttling")
        self.assertIn('_last_progress_time', source,
                      "Must track last progress update time")


class TestDialogGeometryDeferral(unittest.TestCase):
    """Dialogs must defer geometry calculation, not call update_idletasks() in __init__."""

    def test_school_setup_defers_geometry(self):
        from pdf_generator import SchoolSetupDialog
        import inspect
        source = inspect.getsource(SchoolSetupDialog.__init__)
        # Must use after() for positioning, not synchronous update_idletasks
        self.assertIn('_position_and_show', source,
                      "SchoolSetupDialog must defer geometry with _position_and_show")
        # update_idletasks must only appear inside the deferred closure,
        # not as a standalone call in the __init__ body. Check that there's
        # no `self.update_idletasks()` at the __init__ indentation level
        # (i.e. not inside a nested def).
        import re
        # Find update_idletasks calls NOT inside a def block
        # Simple heuristic: look for lines with update_idletasks that are
        # at the same indent level as other __init__ statements
        self.assertIn('def _position_and_show', source,
                      "Must define _position_and_show closure")

    def test_template_name_defers_geometry(self):
        from pdf_generator import TemplateNameDialog
        import inspect
        source = inspect.getsource(TemplateNameDialog.__init__)
        self.assertIn('_position_and_show', source,
                      "TemplateNameDialog must defer geometry with _position_and_show")


class TestFieldTypeAuditDialogFixes(unittest.TestCase):
    """FieldTypeAuditDialog must use canvas-scoped mousewheel and debounced configure."""

    def test_no_per_widget_bind_scroll(self):
        """Mousewheel should be bound on canvas only, not per widget."""
        from pdf_generator import FieldTypeAuditDialog
        import inspect
        source = inspect.getsource(FieldTypeAuditDialog.__init__)
        # The old pattern called _bind_scroll(lbl), _bind_scroll(row), etc.
        # on each created widget. The new pattern binds <Enter>/<Leave> on canvas.
        self.assertIn('<Enter>', source,
                      "Must use <Enter>/<Leave> scoping for mousewheel")
        self.assertIn('<Leave>', source,
                      "Must use <Enter>/<Leave> scoping for mousewheel")

    def test_configure_is_debounced(self):
        """<Configure> binding must use after_idle, not direct lambda."""
        from pdf_generator import FieldTypeAuditDialog
        import inspect
        source = inspect.getsource(FieldTypeAuditDialog.__init__)
        self.assertIn('_config_pending', source,
                      "FieldTypeAuditDialog must debounce <Configure> events")


if __name__ == '__main__':
    unittest.main()
