"""Tests for check_for_update() — the in-app update check."""
import ssl
import sys
import unittest
import urllib.error
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pdf_generator


def _mock_response(tag_name):
    """Mock a urlopen response whose redirect resolved to a release tag page.

    check_for_update sends a HEAD to …/releases/latest and reads resp.url,
    which urllib sets to the URL the 302 resolved to.
    """
    url = ('https://github.com/mrdavearms/bulk-pdf-extractor-and-generator'
           f'/releases/tag/{tag_name}')
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.url = url
    return mock


class TestCheckForUpdate(unittest.TestCase):

    def test_update_available_when_remote_is_newer(self):
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.6')):
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(result['latest'], 'v2.6')
        self.assertTrue(result['html_url'].endswith('/releases/tag/v2.6'))

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

    def test_error_when_no_release_published(self):
        """No releases yet: GitHub serves the index, not a /tag/ URL."""
        mock = MagicMock()
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        mock.url = ('https://github.com/mrdavearms/'
                    'bulk-pdf-extractor-and-generator/releases')
        with patch('urllib.request.urlopen', return_value=mock):
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'error')

    def test_dev_version_returns_up_to_date(self):
        """'dev' current version must never trigger the update prompt."""
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.6')):
            result = pdf_generator.check_for_update('dev')
        self.assertEqual(result['status'], 'up_to_date')

    def test_urlopen_receives_ssl_context(self):
        """urlopen must be called with an ssl.SSLContext for macOS compatibility."""
        with patch('urllib.request.urlopen',
                   return_value=_mock_response('v2.6')) as mock_urlopen:
            pdf_generator.check_for_update('v2.5')
        _args, kwargs = mock_urlopen.call_args
        self.assertIn('context', kwargs, 'urlopen must be called with context= kwarg')
        self.assertIsInstance(kwargs['context'], ssl.SSLContext)

    def test_multi_segment_version_comparison(self):
        """v2.10 is correctly treated as newer than v2.9 (not string comparison)."""
        with patch('urllib.request.urlopen', return_value=_mock_response('v2.10')):
            result = pdf_generator.check_for_update('v2.9')
        self.assertEqual(result['status'], 'update_available')


class TestAvoidsRateLimitedAPI(unittest.TestCase):
    """The check must not use api.github.com.

    The GitHub API allows 60 unauthenticated requests per hour PER IP, and a
    whole school shares one public IP — so on a busy morning most staff would
    be refused and would silently never learn an update exists. Some school
    web filters also block api.github.com while allowing github.com.
    """

    def test_requests_the_plain_github_redirect(self):
        with patch('urllib.request.urlopen',
                   return_value=_mock_response('v2.6')) as mock_urlopen:
            pdf_generator.check_for_update('v2.5')
        req = mock_urlopen.call_args[0][0]
        self.assertNotIn('api.github.com', req.full_url,
                         'must not use the rate-limited GitHub API')
        self.assertTrue(req.full_url.endswith('/releases/latest'), req.full_url)

    def test_uses_head_so_no_page_body_is_downloaded(self):
        with patch('urllib.request.urlopen',
                   return_value=_mock_response('v2.6')) as mock_urlopen:
            pdf_generator.check_for_update('v2.5')
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), 'HEAD')


class TestCertificateFallback(unittest.TestCase):
    """Certificate trust fails in opposite directions on Windows and macOS.

    Windows school networks inspect HTTPS through a proxy whose root
    certificate is in the Windows store but not in certifi; a packaged macOS
    app has no readable system store, so only certifi works. Trying both — in
    the right order per platform — is what makes the check survive either.
    """

    @staticmethod
    def _cafile_order(platform):
        """Return the cafile= argument of each context built, in order.

        Contexts are recorded rather than really built: patching sys.platform
        to 'win32' would make CPython call a Windows-only certificate API that
        does not exist on the machine running the tests.
        """
        seen = []

        def _record(*_args, **kwargs):
            seen.append(kwargs.get('cafile'))
            return MagicMock(spec=ssl.SSLContext)

        with patch.object(pdf_generator.sys, 'platform', platform), \
                patch('ssl.create_default_context', side_effect=_record):
            list(pdf_generator._ssl_contexts())
        return seen

    def test_windows_tries_system_store_first(self):
        import certifi
        # cafile=None means the machine's own certificate store — on Windows
        # that is the only place the school proxy's root certificate lives.
        self.assertEqual(self._cafile_order('win32'), [None, certifi.where()])

    def test_non_windows_tries_bundled_certifi_first(self):
        import certifi
        # A packaged macOS app has no system store OpenSSL can read.
        self.assertEqual(self._cafile_order('darwin'), [certifi.where(), None])

    def test_certificate_failure_retries_with_the_other_bundle(self):
        """A cert error on the first bundle must fall through to the second."""
        cert_error = urllib.error.URLError(ssl.SSLError('CERTIFICATE_VERIFY_FAILED'))
        with patch('urllib.request.urlopen',
                   side_effect=[cert_error, _mock_response('v2.6')]) as mock_urlopen:
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_offline_does_not_retry(self):
        """A non-certificate failure isn't fixed by another CA bundle."""
        offline = urllib.error.URLError('Name or service not known')
        with patch('urllib.request.urlopen', side_effect=offline) as mock_urlopen:
            result = pdf_generator.check_for_update('v2.5')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(mock_urlopen.call_count, 1,
                         'offline must cost one timeout, not two')


class TestUpdateResultIsInline(unittest.TestCase):
    """The update-check result must be reported INLINE, never via a modal dialog.

    On macOS a Tk messagebox can open behind the main window — invisible but
    modal — silently freezing the app (confirmed live on v2.8 AND v2.12.1,
    where a parent= argument was not enough). The outcome is shown in a status
    label instead. This guard stops a messagebox creeping back into the flow.
    """

    def test_show_update_result_uses_no_messagebox(self):
        import inspect
        src = inspect.getsource(pdf_generator.BulkPDFGenerator._show_update_result)
        self.assertNotIn(
            'messagebox', src,
            "_show_update_result must NOT use messagebox — a modal dialog can "
            "hide behind the window and freeze the app on macOS. Report the "
            "result inline via self._update_status_lbl instead.",
        )
        self.assertIn(
            '_update_status_lbl', src,
            "_show_update_result must update the inline status label",
        )


if __name__ == '__main__':
    unittest.main()
