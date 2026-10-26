"""Offline regression: pinned, Zalo-scoped trust and fail-closed startup."""
import hashlib
import os
from pathlib import Path
import ssl
import tempfile
import unittest
import urllib.request
from unittest.mock import patch
from digicert_bundle import ROOT_SHA256, certificate_der
from jat_design import zalo_tls
from jat_design.official_api import Transport
from jat_design.gemini_client import Gemini

def trust_signature(handler):
    return None if handler._context is None else {hashlib.sha256(c).hexdigest() for c in handler._context.get_ca_certs(binary_form=True)}


ROOT = Path(__file__).resolve().parents[1]/'certs'/'DigiCertGlobalRootG3.pem'


class ZaloCATests(unittest.TestCase):
    def test_shipped_root_is_exact_pinned_der_and_only_trust_anchor(self):
        self.assertEqual(hashlib.sha256(certificate_der(ROOT.read_bytes())).hexdigest().upper(), ROOT_SHA256)
        context = zalo_tls.root_context(ROOT)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_flags & 0x80000, 0)
        self.assertEqual(len(context.get_ca_certs()), 1)

    def test_win7_context_is_used_by_zalo_only_gemini_keeps_default(self):
        expected_google = trust_signature(urllib.request.HTTPSHandler())
        old_default = ssl._create_default_https_context
        old_environment = os.environ.get('SSL_CERT_FILE')
        with patch.dict(os.environ, {zalo_tls.ENVIRONMENT_KEY: str(ROOT)}):
            transport = Transport('synthetic-offline-token')
            gemini = Gemini('synthetic-offline-key', 'Synthetic prompt')
        zalo_handler = next(h for h in transport._opener.handlers if isinstance(h, urllib.request.HTTPSHandler))
        google_handler = next(h for h in gemini.opener.handlers if isinstance(h, urllib.request.HTTPSHandler))
        self.assertIsNotNone(zalo_handler._context)
        self.assertEqual(trust_signature(google_handler), expected_google)
        self.assertIs(ssl._create_default_https_context, old_default)
        self.assertEqual(os.environ.get('SSL_CERT_FILE'), old_environment)
        # Redirect rejection remains part of the existing transport.
        self.assertTrue(any(type(h).__name__ == 'NoRedirect' for h in transport._opener.handlers))

    def test_default_launch_without_setting_keeps_original_https(self):
        expected_default = trust_signature(urllib.request.HTTPSHandler())
        with patch.dict(os.environ):
            os.environ.pop(zalo_tls.ENVIRONMENT_KEY, None)
            self.assertIsNone(zalo_tls.configured_context())
            transport = Transport('synthetic-offline-token')
        handler = next(h for h in transport._opener.handlers if isinstance(h, urllib.request.HTTPSHandler))
        self.assertEqual(trust_signature(handler), expected_default)

    def test_missing_or_modified_ca_prevents_opener_creation_no_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder)/'private-path.pem'
            for data in (None, ROOT.read_bytes().replace(b'MI', b'MJ', 1), ROOT.read_bytes()*2):
                if data is not None:
                    bad.write_bytes(data)
                with patch.dict(os.environ, {zalo_tls.ENVIRONMENT_KEY: str(bad)}), patch('urllib.request.build_opener') as network:
                    with self.assertRaises(ValueError) as error:
                        Transport('synthetic-offline-token')
                    self.assertNotIn('private-path', str(error.exception))
                    network.assert_not_called()

    def test_invalid_clock_or_expired_root_fails_closed(self):
        with patch('jat_design.zalo_tls.time.time', return_value=2200000000):
            with self.assertRaises(ValueError):
                zalo_tls.root_context(ROOT)

    def test_read_only_probe_selects_zalo_context_without_replacing_google_context(self):
        from jat_design.https_probe import check_https
        used = []
        class Response:
            status = 404
            def __enter__(self): return self
            def __exit__(self, *args): pass
        class Opener:
            def __init__(self, context): self.context = context
            def open(self, url, timeout):
                used.append((url, self.context)); return Response()
        def build(*handlers):
            return Opener(next(h._context for h in handlers if isinstance(h, urllib.request.HTTPSHandler)))
        with patch.dict(os.environ, {zalo_tls.ENVIRONMENT_KEY: str(ROOT)}), patch('urllib.request.build_opener', side_effect=build):
            self.assertEqual(check_https(output=lambda _: None), 0)
        self.assertEqual(len(used), 2)
        self.assertIn('googleapis.com', used[0][0])
        self.assertIn('zaloplatforms.com', used[1][0])
        self.assertIsNot(used[0][1], used[1][1])
        ca = used[1][1].get_ca_certs(binary_form=True)
        self.assertEqual([hashlib.sha256(c).hexdigest().upper() for c in ca], [ROOT_SHA256])
