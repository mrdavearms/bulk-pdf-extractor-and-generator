"""Lifecycle / robustness structural tests (items 3 and 6).

These follow the existing inspect.getsource() convention used elsewhere in the
suite: the generation worker and window-close paths are tightly coupled to a
live Tk root and a real PDF, so we assert the safety structure is present
rather than spinning up a GUI.
"""
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_generator import BulkPDFGenerator


class TestCloseDuringGeneration(unittest.TestCase):
    """Item 3: closing the window mid-generation must stop the worker cleanly."""

    def test_on_closing_sets_closing_flag(self):
        src = inspect.getsource(BulkPDFGenerator.on_closing)
        self.assertIn('self._closing = True', src,
                      "on_closing must set the _closing flag before destroy()")
        # Flag must be set before the window is torn down.
        self.assertLess(src.index('self._closing = True'),
                        src.index('self.root.destroy()'),
                        "_closing must be set BEFORE root.destroy()")

    def test_generation_loop_checks_closing_flag(self):
        src = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn('self._closing', src,
                      "run_generation_tab3 must check self._closing so it can "
                      "stop when the window is closing")

    def test_closing_flag_initialised(self):
        src = inspect.getsource(BulkPDFGenerator.__init__)
        self.assertIn('self._closing = False', src,
                      "__init__ must initialise self._closing = False")


class TestTemplateLoadRefreshesTable(unittest.TestCase):
    """Item 6: the fields table must populate on load even when the template
    carried no saved data types."""

    def test_display_called_outside_saved_types_gate(self):
        src = inspect.getsource(BulkPDFGenerator.load_template_config)
        # The refresh must be guarded by analyzed_fields, NOT by saved_types —
        # otherwise legacy/hand-edited templates load with a blank table.
        self.assertIn('if self.analyzed_fields:\n', src)
        # Locate the data-type restore block and ensure display happens after,
        # gated on analyzed_fields rather than nested under `if saved_types`.
        self.assertRegex(
            src,
            r"if self\.analyzed_fields:\s*\n\s*self\.display_analyzed_fields\(\)",
        )


if __name__ == '__main__':
    unittest.main()
