"""Start-up smoke test: build the real main window the way main() does.

Releases v2.15-v2.17 were built with ttkbootstrap 2.x, which removed the
`autostyle` option, so the app crashed before its window appeared. Every
other test in this suite avoids Tk and passed regardless. This one opens the
window (hidden) and walks every tab.

It runs on the Windows and macOS CI runners, which have a display. It skips
where Tk cannot start, such as the headless Linux `test` job.
"""
import logging
import tempfile
import tkinter as tk
import traceback
import unittest
from unittest import mock


class TestAppStarts(unittest.TestCase):

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = (
            lambda *exc: self.errors.append(''.join(traceback.format_exception(*exc))))
        self.data_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        # Close the app.log the app opened in data_dir: Windows cannot delete
        # an open file, and later tests must not log into a deleted folder.
        logger = logging.getLogger('bulk_pdf_generator')
        for handler in list(logger.handlers):
            if self.data_dir.name in getattr(handler, 'baseFilename', ''):
                logger.removeHandler(handler)
                handler.close()
        self.data_dir.cleanup()

    def test_main_window_builds_and_every_tab_opens(self):
        import pdf_generator as pg
        # Keep the test out of the real ~/Documents/BulkPDFGenerator and off
        # the network.
        with mock.patch.object(pg, '_resolve_data_dir', return_value=self.data_dir.name), \
             mock.patch.object(pg.BulkPDFGenerator, '_maybe_auto_check_update', lambda self: None):
            pg.resolve_font_family()
            pg.apply_dark_theme(self.root)
            app = pg.BulkPDFGenerator(self.root)
            self.root.update()
            for tab_id in app.notebook.tabs():
                if app.notebook.tab(tab_id, 'state') == 'disabled':
                    continue
                app.notebook.select(tab_id)
                self.root.update()
        self.assertEqual(self.errors, [], '\n'.join(self.errors))


if __name__ == '__main__':
    unittest.main()
