"""Tests for check_for_update() GitHub Releases API function."""
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pdf_generator


def _mock_response(tag_name, html_url='https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.6'):
    """Build a mock urllib response context manager."""
    payload = json.dumps({'tag_name': tag_name, 'html_url': html_url}).encode()
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = payload
    return mock


class TestCheckForUpdate(unittest.TestCase):

    def test_update_available_when_remote_is_newer(self):
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.6')):
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(result['latest'], 'v2.6')
        self.assertIn('html_url', result)

    def test_up_to_date_when_versions_match(self):
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.6')):
            result = pdf_generator.check_for_update('v2.6')
        self.assertEqual(result['status'], 'up_to_date')
        self.assertEqual(result['latest'], 'v2.6')

    def test_up_to_date_when_local_is_newer(self):
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.5')):
            result = pdf_generator.check_for_update('v2.6')
        self.assertEqual(result['status'], 'up_to_date')

    def test_error_on_network_failure(self):
        with patch('urllib.request.urlopen', side_effect=Exception('timeout')):
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'error')
        self.assertIn('message', result)

    def test_error_on_malformed_json(self):
        mock = MagicMock()
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        mock.read.return_value = b'not json'
        with patch('urllib.request.urlopen', return_value=mock):
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'error')

    def test_dev_version_returns_up_to_date(self):
        """'dev' current version must never trigger the update prompt."""
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.6')):
            result = pdf_generator.check_for_update('dev')
        self.assertEqual(result['status'], 'up_to_date')

    def test_multi_segment_version_comparison(self):
        """v2.10 is correctly treated as newer than v2.9 (not string comparison)."""
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.10')):
            result = pdf_generator.check_for_update('v2.9')
        self.assertEqual(result['status'], 'update_available')


if __name__ == '__main__':
    unittest.main()
