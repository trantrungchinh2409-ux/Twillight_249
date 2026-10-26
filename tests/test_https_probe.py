import contextlib
import io
import socket
import ssl
import unittest
import urllib.error
from unittest.mock import patch
from jat_design.https_probe import check_https, error_fields, TARGETS


class ProbeTests(unittest.TestCase):
    def test_certificate_failure_exposes_code_not_message(self):
        error = ssl.SSLCertVerificationError(1, 'private CA/token/hostname')
        error.verify_code = 20
        error.verify_message = 'private company CA'
        self.assertEqual(error_fields(urllib.error.URLError(error)), {'error': 'certificate_verification_failed', 'certificate_code': 20})
        self.assertNotIn('private', str(error_fields(error)))

    def test_tls_reason_and_network_fields_are_allowlisted(self):
        error = ssl.SSLError(1, 'sensitive')
        error.reason = 'SSLV3_ALERT_HANDSHAKE_FAILURE'
        self.assertEqual(error_fields(error)['tls_reason'], 'SSLV3_ALERT_HANDSHAKE_FAILURE')
        error.reason = 'sensitive-token'
        self.assertEqual(error_fields(error)['tls_reason'], 'unclassified')
        self.assertEqual(error_fields(socket.timeout()), {'error': 'timeout'})
        self.assertEqual(error_fields(socket.gaierror()), {'error': 'dns_failed'})
        self.assertEqual(error_fields(OSError(10054, 'sensitive proxy')), {'error': 'network_failed', 'os_code': 10054})

    def test_proxy_diagnostics_never_print_url_or_credentials(self):
        e = urllib.error.URLError('Tunnel connection failed: 403 Forbidden https://user:private@proxy')
        self.assertEqual(error_fields(e), {'error': 'proxy_connect_rejected', 'proxy_http': 403})
        self.assertEqual(error_fields(urllib.error.URLError('private error')), {'error': 'connection_failed'})

    def test_google_404_is_tls_success_zalo_error_is_failure_no_credentials(self):
        calls, lines = [], []
        error = ssl.SSLCertVerificationError(1, 'sensitive'); error.verify_code = 20
        class Fake:
            def open(self, url, timeout):
                calls.append((url, timeout))
                if len(calls) == 1:
                    raise urllib.error.HTTPError(url, 404, 'private', {}, None)
                raise urllib.error.URLError(error)
        self.assertEqual(check_https(lines.append, Fake()), 1)
        self.assertEqual(calls, [(url, 20) for _, url in TARGETS])
        text = '\n'.join(lines)
        self.assertIn('Google: HTTPS certificate validation passed, HTTP 404', text)
        self.assertIn('certificate_code=20 error=certificate_verification_failed', text)
        self.assertNotIn('sensitive', text)
        self.assertNotIn('private', text)

    def test_real_opener_configuration_keeps_verification(self):
        lines = []
        class Fake:
            def open(self, url, timeout):
                raise urllib.error.HTTPError(url, 404, 'unused', {}, None)
        with patch('urllib.request.build_opener', return_value=Fake()) as build:
            self.assertEqual(check_https(lines.append), 0)
            handler = build.call_args[0][1]
            self.assertEqual(handler._context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(handler._context.check_hostname)
