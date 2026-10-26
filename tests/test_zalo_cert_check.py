import base64
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
import zalo_cert_check as cert


class CertCheckTests(unittest.TestCase):
    def test_public_ca_requires_independent_fingerprint_and_keeps_verify_flags(self):
        public = next(d for d in ssl.create_default_context().get_ca_certs(binary_form=True) if cert.is_ca(d))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'public-root.pem'
            path.write_text(ssl.DER_cert_to_PEM_cert(public), encoding='ascii')
            original = ssl.create_default_context()
            old_flags = original.verify_flags
            context, fingerprint = cert.approved_context(lambda: original, path, cert.fingerprint(public))
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_flags, old_flags)
            self.assertEqual(fingerprint, cert.fingerprint(public))
            for wrong in ['', '0'*64, 'approve-without-fingerprint']:
                with self.assertRaises(ValueError):
                    cert.approved_context(ssl.create_default_context, path, wrong)
            path.write_text('-----BEGIN PRIVATE KEY-----\nsensitive\n-----END PRIVATE KEY-----', encoding='ascii')
            with self.assertRaises(ValueError):
                cert.approved_context(ssl.create_default_context, path, '0'*64)

    def test_reject_malformed_or_non_ca_der(self):
        for der in [b'', b'\x30\x80', b'\x30\x02\x30\x00', b'\x30\x04\x30\x00xx']:
            try:
                result = cert.is_ca(der)
            except ValueError:
                result = False
            self.assertFalse(result)

    def test_windows_ipc_never_exposes_subject_proxy_or_raw_certificate(self):
        text = '\n'.join(['WINDOWS_HTTPS=PASS', 'WINDOWS_HTTP=404', 'SUBJECT=private company',
            'ROUTE_B64='+base64.b64encode(b'http://private-proxy:8080').decode(),
            'CERT_0_DER='+base64.b64encode(b'public-certificate-bytes').decode(),
            'LEAF_DER='+base64.b64encode(b'leaf-public').decode(), 'WINDOWS_ERROR=secret',
            'CHAIN_STATUS_FLAGS=32'])
        with patch.object(cert, 'python_route', return_value='http://private-proxy:8080'):
            result = cert.parse_windows_output(text)
        self.assertEqual(result['ROUTE_MATCH'], 'YES')
        self.assertEqual(result['certificates'], [cert.fingerprint(b'public-certificate-bytes')])
        for word in ['private', 'secret', 'public-certificate-bytes']:
            self.assertNotIn(word, str(result))

    def test_different_proxy_route_cannot_be_claimed_same(self):
        text = 'ROUTE_B64='+base64.b64encode(b'DIRECT').decode()
        with patch.object(cert, 'python_route', return_value='http://approved-proxy:8080'):
            self.assertEqual(cert.parse_windows_output(text)['ROUTE_MATCH'], 'NO_OR_UNKNOWN')

    def test_windows_probe_respects_execution_policy_and_hides_stderr(self):
        class R:
            returncode = 1
            stdout = b''
            stderr = b'private path or company policy'
        with patch.object(cert.os, 'name', 'nt'), patch('subprocess.run', return_value=R()) as run:
            result = cert.windows_probe()
        command = run.call_args[0][0]
        self.assertNotIn('-ExecutionPolicy', command)
        self.assertNotIn('-EncodedCommand', command)
        self.assertIn('-File', command)
        self.assertEqual(result['WINDOWS_PROBE_ERROR'], 'POWERSHELL_POLICY_OR_RUNTIME_BLOCKED')
        self.assertNotIn('private', str(result))

    def test_unverified_tls_is_never_used_for_chain_retrieval(self):
        source = Path(cert.__file__).read_text(encoding='utf-8')
        ps = (cert.BASE/'inspect_zalo_windows_chain.ps1').read_text(encoding='utf-8')
        self.assertNotIn('CERT_NONE', source)
        self.assertNotIn('_create_unverified_context', source)
        self.assertNotIn('SecurityFlags', ps)
        self.assertNotIn('ServerCertificateValidationCallback =', ps)
        self.assertNotIn('Set-ExecutionPolicy', ps)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows certificate stores required')
    def test_native_windows_store_read_only(self):
        context = ssl.create_default_context()
        result = cert.store_snapshot(context)
        self.assertTrue(result['PYTHON'])
        self.assertTrue(result['ROOT'])
        self.assertTrue(all(len(sha) == 64 for store in result.values() for sha in store))

    def test_known_windows_distrust_is_not_overridden_by_ca_file(self):
        class C:
            def get_ca_certs(self, binary_form=False): return []
        lines = []
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'APPROVED_CA.pem').write_text('public placeholder', encoding='ascii')
            with patch.object(cert, 'BASE', Path(folder)), patch('ssl.create_default_context', return_value=C()), patch.object(cert, 'store_snapshot', return_value={k:set() for k in ['PYTHON','ROOT','CA','ROOT_SERVER_AUTH','CA_SERVER_AUTH']}), patch.object(cert.tls, 'probe', return_value=False), patch.object(cert, 'windows_probe', return_value={'CHAIN_STATUS_FLAGS':67108864,'certificates':[]}), patch('builtins.input', side_effect=AssertionError('must not offer override')), patch('builtins.print', side_effect=lambda *a: lines.append(' '.join(map(str,a)))):
                self.assertEqual(cert.main(), 1)
        self.assertIn('resolve with IT', '\n'.join(lines))
