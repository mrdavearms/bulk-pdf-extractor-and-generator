"""Tests for _generate_version.py version baking."""
import os
import sys
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

import _generate_version


class TestGenerateVersion(unittest.TestCase):

    def _run_with_tmp(self, fake_check_output, tmp):
        """Helper: run main() with git calls mocked and output redirected to tmp.

        Patch abspath to return a fake script path *inside* tmp so that
        dirname(abspath(__file__)) resolves to tmp itself.
        """
        fake_script = str(Path(tmp) / '_generate_version.py')
        with patch.object(_generate_version.subprocess, 'check_output',
                          side_effect=fake_check_output):
            with patch.object(_generate_version.os.path, 'abspath', return_value=fake_script):
                _generate_version.main()

    def test_writes_build_version_from_tag(self):
        """BUILD_VERSION is written when a git tag exists."""
        def fake(cmd, **kwargs):
            return {
                ('git', 'log', '-1', '--format=%h'): 'abc1234',
                ('git', 'log', '-1', '--format=%cd', '--date=format:%d %b %Y'): '17 Mar 2026',
                ('git', 'describe', '--tags', '--abbrev=0'): 'v2.6',
            }[tuple(cmd)]

        with tempfile.TemporaryDirectory() as tmp:
            self._run_with_tmp(fake, tmp)
            content = Path(tmp, '_version.py').read_text()

        self.assertIn('BUILD_COMMIT = "abc1234"', content)
        self.assertIn('BUILD_DATE = "17 Mar 2026"', content)
        self.assertIn('BUILD_VERSION = "v2.6"', content)

    def test_writes_dev_when_no_tag(self):
        """BUILD_VERSION falls back to 'dev' when no git tag exists."""
        def fake(cmd, **kwargs):
            if 'describe' in cmd:
                raise subprocess.CalledProcessError(128, cmd)
            return {
                ('git', 'log', '-1', '--format=%h'): 'abc1234',
                ('git', 'log', '-1', '--format=%cd', '--date=format:%d %b %Y'): '17 Mar 2026',
            }[tuple(cmd)]

        with tempfile.TemporaryDirectory() as tmp:
            self._run_with_tmp(fake, tmp)
            content = Path(tmp, '_version.py').read_text()

        self.assertIn('BUILD_VERSION = "dev"', content)


if __name__ == '__main__':
    unittest.main()
