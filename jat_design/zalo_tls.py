"""Optional pinned Zalo-only CA context. No global SSL or trust-store changes."""
import os
from pathlib import Path
import ssl
import time
from digicert_bundle import ROOT_SHA256, ROOT_CN, certificate_der, describe, sha256

ENVIRONMENT_KEY = 'JAT_ZALO_CA_FILE'


def root_context(path):
    """Accept only the pinned public root, fail closed without network fallback."""
    try:
        with Path(path).open('rb') as source:
            der = certificate_der(source.read(65537))
        if sha256(der) != ROOT_SHA256:
            raise ValueError('root_pin_mismatch')
        info = describe(der)
        if info['subject_cn'] != ROOT_CN or info['issuer_cn'] != ROOT_CN:
            raise ValueError('root_identity_mismatch')
        now = time.time()
        if not ssl.cert_time_to_seconds(info['not_before']) <= now <= ssl.cert_time_to_seconds(info['not_after']):
            raise ValueError('root_time_invalid')
        # Explicit cadata: only this Zalo context trusts this CA, not default stores.
        context = ssl.create_default_context(cadata=ssl.DER_cert_to_PEM_cert(der))
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ValueError('verification_required')
        if context.verify_flags & 0x80000:
            raise ValueError('partial_chain_not_allowed')
        if {sha256(c) for c in context.get_ca_certs(binary_form=True)} != {ROOT_SHA256}:
            raise ValueError('unexpected_trust_anchor')
        return context
    except Exception:
        # Do not expose file paths, proxy data or arbitrary exception messages.
        raise ValueError('Zalo CA validation failed; no request made. Keep TLS verification enabled.') from None


def configured_context():
    # Existing Win11/default launches retain the original standard-library HTTPS.
    if ENVIRONMENT_KEY not in os.environ:
        return None
    return root_context(os.environ[ENVIRONMENT_KEY])
