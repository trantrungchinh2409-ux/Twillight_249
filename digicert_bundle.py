"""Pinned public DigiCert bundle utilities; no Windows-store imports or bot dependencies."""
import base64
import ctypes
import hashlib
import os
from pathlib import Path
import re
import ssl
import tempfile
import time

ROOT_SHA256 = '31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0'
ROOT_URL = 'https://cacerts.digicert.com/DigiCertGlobalRootG3.crt'
ROOT_CN = 'DigiCert Global Root G3'
INTERMEDIATE_CN = 'RapidSSL TLS ECC CA G1'
BASE = Path(__file__).resolve().parent
CA_DIR = BASE/'ca_digicert'


def sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def certificate_der(data):
    if len(data) > 65536:
        raise ValueError('certificate_too_large')
    if data.strip().startswith(b'-----BEGIN'):
        m = re.fullmatch(rb'\s*-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+)\s*-----END CERTIFICATE-----\s*', data)
        if not m:
            raise ValueError('one_public_certificate_required')
        return base64.b64decode(b''.join(m[1].split()), validate=True)
    if not data or data[0] != 48:
        raise ValueError('certificate_format_invalid')
    return data


def describe(der):
    # Public CA metadata decoding only; this is not signature verification.
    with tempfile.TemporaryDirectory(prefix='jat-public-ca-') as folder:
        path = Path(folder)/'public.pem'
        path.write_text(ssl.DER_cert_to_PEM_cert(der), encoding='ascii')
        info = ssl._ssl._test_decode_cert(str(path))
    def cn(field):
        return next((value for rdn in info.get(field, ()) for key, value in rdn if key == 'commonName'), '')
    return {'subject_cn':cn('subject'), 'issuer_cn':cn('issuer'),
            'not_before':info['notBefore'], 'not_after':info['notAfter'],
            'ocsp':list(info.get('OCSP', ())), 'crl':list(info.get('crlDistributionPoints', ()))}


def signature_windows(subject, issuer):
    """Verify a certificate's signature using explicit issuer in memory, not trust store."""
    if os.name != 'nt':
        raise RuntimeError('native_windows_required')
    api = ctypes.WinDLL('crypt32', use_last_error=True)
    api.CertCreateCertificateContext.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
    api.CertCreateCertificateContext.restype = ctypes.c_void_p
    api.CertFreeCertificateContext.argtypes = [ctypes.c_void_p]
    api.CertFreeCertificateContext.restype = ctypes.c_int
    api.CryptVerifyCertificateSignatureEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    api.CryptVerifyCertificateSignatureEx.restype = ctypes.c_int
    buffers = [ctypes.create_string_buffer(data) for data in (subject, issuer)]
    contexts = []
    try:
        for data, buffer in zip((subject, issuer), buffers):
            context = api.CertCreateCertificateContext(1, buffer, len(data))
            if not context:
                raise ValueError('certificate_decode_failed')
            contexts.append(context)
        # SUBJECT_CERT=2, ISSUER_CERT=2. No ignore-error flags, no store installation.
        return bool(api.CryptVerifyCertificateSignatureEx(None, 1, 2, contexts[0], 2, contexts[1], 0, None))
    finally:
        for context in contexts:
            api.CertFreeCertificateContext(context)


def validate_public_cas(root, intermediate, verify_signature=signature_windows):
    if sha256(root) != ROOT_SHA256:
        raise ValueError('root_sha256_mismatch')
    a, b = describe(root), describe(intermediate)
    if a['subject_cn'] != ROOT_CN or a['issuer_cn'] != ROOT_CN:
        raise ValueError('root_identity_mismatch')
    if b['subject_cn'] != INTERMEDIATE_CN or b['issuer_cn'] != ROOT_CN:
        raise ValueError('intermediate_identity_mismatch')
    now = time.time()
    for item in (a, b):
        if not ssl.cert_time_to_seconds(item['not_before']) <= now <= ssl.cert_time_to_seconds(item['not_after']):
            raise ValueError('ca_time_invalid_check_clock')
    if not verify_signature(root, root):
        raise ValueError('root_signature_failed_or_crypto_unsupported')
    if not verify_signature(intermediate, root):
        raise ValueError('intermediate_signature_failed_or_crypto_unsupported')
    return a, b


def make_context(pem):
    # Passing explicit cadata means no default Windows/OpenSSL CA store is loaded.
    context = ssl.create_default_context(cadata=pem)
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ValueError('tls_verification_not_enabled')
    # Never permit an intermediate to substitute for the pinned root anchor.
    if context.verify_flags & 0x80000:  # X509_V_FLAG_PARTIAL_CHAIN, not exposed on all 3.8 builds.
        raise ValueError('partial_chain_not_allowed')
    return context
