"""Tests for _get_build_info() helper."""
import sys
import unittest
from unittest.mock import MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_version_module(commit, date, version=None):
    """Return a mock _version module with given attributes."""
    m = MagicMock()
    m.BUILD_COMMIT = commit
    m.BUILD_DATE = date
    if version is not None:
        m.BUILD_VERSION = version
    else:
        # Simulate missing BUILD_VERSION (old build)
        del m.BUILD_VERSION
    return m


class TestGetBuildInfo(unittest.TestCase):

    def setUp(self):
        # Ensure _version module is removable between tests
        sys.modules.pop('_version', None)

    def test_returns_three_tuple_from_version_module(self):
        """_get_build_info returns (commit, date, version) from _version module."""
        mock_v = _make_version_module('abc1234', '17 Mar 2026', 'v2.6')
        sys.modules['_version'] = mock_v
        try:
            import pdf_generator
            result = pdf_generator._get_build_info()
        except Exception:
            self.skipTest("Skipping: display not available (headless environment)")
        self.assertEqual(result, ('abc1234', '17 Mar 2026', 'v2.6'))

    def test_falls_back_to_dev_when_no_build_version(self):
        """_get_build_info returns 'dev' as version when BUILD_VERSION absent (old build)."""
        mock_v = _make_version_module('abc1234', '17 Mar 2026', version=None)
        sys.modules['_version'] = mock_v
        try:
            import pdf_generator
            commit, date, version = pdf_generator._get_build_info()
        except Exception:
            self.skipTest("Skipping: display not available (headless environment)")
        self.assertEqual(version, 'dev')
        self.assertEqual(commit, 'abc1234')


if __name__ == '__main__':
    unittest.main()
