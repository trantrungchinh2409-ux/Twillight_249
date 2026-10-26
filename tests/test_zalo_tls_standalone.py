import ssl
import socket
import unittest
import urllib.error
from unittest.mock import patch
import check_zalo_tls as probe


class StandaloneTlsTests(unittest.TestCase):
    def test_cert_reason_safe_and_company_cause_not_invented(self):
        e = ssl.SSLCertVerificationError(1, 'private company CA'); e.verify_code = 20
        kind, fields = probe.classify(urllib.error.URLError(e))
        self.assertEqual(kind, 'CERTIFICATE')
        self.assertEqual(fields['certificate_code'], 20)
        self.assertNotIn('private', str(fields))
        self.assertNotIn('company', str(fields))

    def test_explicit_proxy_refusal_distinct_from_unknown_network_source(self):
        kind, data = probe.classify(urllib.error.URLError('Tunnel connection failed: 403 Forbidden user:secret@proxy'))
        self.assertEqual((kind, data['proxy_http']), ('PROXY_CONNECT', 403))
        self.assertNotIn('secret', str(data))
        for e, expected in [(socket.timeout(), 'TIMEOUT'), (socket.gaierror(), 'DNS'), (OSError(10054, 'private'), 'NETWORK')]:
            self.assertEqual(probe.classify(e)[0], expected)
            self.assertIn('source_unknown', str(probe.classify(e)[1]))

    def test_404_and_403_verify_tls_but_not_company_blocking(self):
        for code in [404, 403]:
            lines = []
            class Fake:
                def open(self, url, timeout):
                    raise urllib.error.HTTPError(url, code, 'private', {}, None)
            self.assertTrue(probe.probe('Zalo', 'bot-api.zaloplatforms.com', Fake(), lines.append))
            self.assertIn('HTTPS=PASS', lines[0])
            self.assertNotIn('private', str(lines))

    def test_run_preserves_ssl_and_reports_only_proxy_presence(self):
        class Fake:
            def open(self, url, timeout):
                raise urllib.error.HTTPError(url, 404, 'private', {}, None)
        lines = []
        with patch.object(probe, 'dns_status', return_value='FAIL'), patch('urllib.request.getproxies', return_value={'https':'http://u:secret@proxy'}), patch('urllib.request.build_opener', return_value=Fake()) as build:
            self.assertEqual(probe.run(lines.append), 0)
            self.assertTrue(build.call_args[0][1]._context.check_hostname)
            self.assertEqual(build.call_args[0][1]._context.verify_mode, ssl.CERT_REQUIRED)
        text = '\n'.join(lines)
        self.assertIn('ZALO_TLS_RESULT=PASS', text)
        self.assertIn('PROXY_CONFIGURED=YES', text)
        self.assertNotIn('secret', text)
        self.assertNotIn('u:', text)

    def test_dns_lookup_does_not_disclose_addresses(self):
        with patch('socket.getaddrinfo', return_value=[('private-address',)]):
            self.assertEqual(probe.dns_status('bot-api.zaloplatforms.com'), 'PASS')
        with patch('socket.getaddrinfo', side_effect=socket.gaierror('private resolver')):
            self.assertEqual(probe.dns_status('bot-api.zaloplatforms.com'), 'FAIL')
