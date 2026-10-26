import os
from pathlib import Path
import ssl
import unittest
import urllib.error
from unittest.mock import patch
import digicert_bundle as bundle
import check_zalo_digicert as checker
from scripts.fetch_digicert_bundle import validate_url
from scripts import fetch_digicert_bundle as fetcher


class DigiCertBundleTests(unittest.TestCase):
    def test_root_tampering_fails_before_any_signature_or_network(self):
        with self.assertRaisesRegex(ValueError,'root_sha256_mismatch'):
            bundle.validate_public_cas(b'invalid-public-root',b'intermediate',lambda *a:self.fail('must not verify wrong pin'))

    def test_private_context_loads_only_explicit_ca_and_keeps_hostname_verification(self):
        der=ssl.create_default_context().get_ca_certs(binary_form=True)[0]
        context=bundle.make_context(ssl.DER_cert_to_PEM_cert(der))
        self.assertEqual({bundle.sha256(d) for d in context.get_ca_certs(binary_form=True)},{bundle.sha256(der)})
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_flags & 0x80000,0)

    def test_source_downloads_never_allow_insecure_or_foreign_redirects(self):
        validate_url(bundle.ROOT_URL)
        for url in ['http://cacerts.digicert.com/root.crt','https://cacerts.digicert.com.evil/root.crt','https://user:secret@cacerts.digicert.com/root.crt','https://cacerts.digicert.com:8443/root.crt']:
            with self.assertRaises(ValueError):validate_url(url)

    def test_one_public_certificate_only(self):
        der=ssl.create_default_context().get_ca_certs(binary_form=True)[0]
        pem=ssl.DER_cert_to_PEM_cert(der).encode('ascii')
        self.assertEqual(bundle.certificate_der(pem),der)
        for raw in [pem+pem,b'-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----',b'x'*65537]:
            with self.assertRaises(ValueError):bundle.certificate_der(raw)

    def test_probe_404_is_verified_tls_not_auth_and_errors_never_leak(self):
        context=ssl.create_default_context()
        class Fake:
            def open(self,url,timeout):raise urllib.error.HTTPError(url,404,'private',{},None)
        with patch('builtins.print') as output:
            result=checker.probe('CHECK',context,opener=Fake())
        self.assertEqual(result['tls'],'PASS')
        self.assertEqual(result['http'],404)
        self.assertNotIn('private',str(output.call_args))
        class Fail:
            def open(self,url,timeout):raise ssl.SSLCertVerificationError(1,'private CA details')
        with patch('builtins.print') as output:
            result=checker.probe('CHECK',context,opener=Fail())
        self.assertEqual(result['tls'],'FAIL')
        self.assertNotIn('private',str(output.call_args))

    def test_process_ca_environment_always_restored_without_bot_launch(self):
        with patch.dict(os.environ,{'SSL_CERT_FILE':'original-private-path'}),patch.object(checker,'probe',return_value={'tls':'PASS'}) as probe:
            self.assertTrue(checker.integration_check(Path('public-ca.pem')))
            self.assertEqual(probe.call_count,2)
            self.assertEqual(os.environ['SSL_CERT_FILE'],'original-private-path')
        with patch.dict(os.environ,{'SSL_CERT_FILE':'original-private-path'}),patch.object(checker,'probe',side_effect=OSError('private')):
            with self.assertRaises(OSError):checker.integration_check(Path('public-ca.pem'))
            self.assertEqual(os.environ['SSL_CERT_FILE'],'original-private-path')

    def test_downloaded_wrong_root_stops_before_intermediate_or_file_writes(self):
        with patch.object(fetcher, 'download', return_value=b'0untrusted') as download, patch.object(fetcher, 'validate_public_cas') as verify:
            with self.assertRaisesRegex(ValueError, 'root_sha256_mismatch'):
                fetcher.main()
        self.assertEqual(download.call_count, 1)
        verify.assert_not_called()

    def test_build_failure_report_contains_safe_codes_not_exception_text(self):
        fetcher.EVENTS.clear()
        with patch.object(fetcher, 'CURRENT_URL', bundle.ROOT_URL):
            fetcher.record(urllib.error.URLError('private-company-user:secret-password'))
        self.assertNotIn('secret-password', str(fetcher.EVENTS))
        self.assertEqual(fetcher.EVENTS[-1]['official_url'], bundle.ROOT_URL)
        fetcher.EVENTS.clear()

    @unittest.skipUnless(os.name=='nt'  and (bundle.CA_DIR/'SOURCE.json').exists(),'Official bundle/native Windows build required')
    def test_official_bundle_real_pins_native_signatures_and_dates(self):
        root_pem,combined,meta=checker.verified_files()
        self.assertEqual(bundle.sha256(bundle.certificate_der(root_pem.encode('ascii'))),bundle.ROOT_SHA256)
        self.assertIn('RapidSSL TLS ECC CA G1',meta['intermediate']['subject_cn'])
        self.assertEqual(len(bundle.make_context(combined).get_ca_certs(binary_form=True)),2)
