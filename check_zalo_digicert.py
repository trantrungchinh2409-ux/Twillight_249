"""Credential-free DigiCert root/intermediate TLS test, isolated from Windows trust/bot."""
import argparse
import json
import os
from pathlib import Path
import ssl
import urllib.error
import urllib.parse
import urllib.request
from digicert_bundle import (CA_DIR, ROOT_SHA256, ROOT_URL, certificate_der, sha256,
    validate_public_cas, make_context)
from check_zalo_tls import NoRedirect, classify

ZALO = 'https://bot-api.zaloplatforms.com/'
GOOGLE = 'https://generativelanguage.googleapis.com/'


def verified_files(folder=CA_DIR):
    root = certificate_der((folder/'DigiCertGlobalRootG3.pem').read_bytes())
    intermediate = certificate_der((folder/'RapidSSLTLSECCCAG1.pem').read_bytes())
    meta = json.loads((folder/'SOURCE.json').read_text(encoding='utf-8'))
    if sha256(root) != ROOT_SHA256 or meta.get('root_sha256') != ROOT_SHA256 or meta.get('root_source') != ROOT_URL:
        raise ValueError('root_pin_or_source_mismatch')
    source = urllib.parse.urlsplit(meta.get('intermediate_source', ''))
    if source.scheme != 'https' or source.hostname != 'cacerts.digicert.com' or source.username or source.password or source.port not in (None,443):
        raise ValueError('intermediate_source_invalid')
    if sha256(intermediate) != meta.get('intermediate_sha256'):
        raise ValueError('intermediate_hash_mismatch')
    validate_public_cas(root, intermediate)
    root_pem = ssl.DER_cert_to_PEM_cert(root)
    intermediate_pem = ssl.DER_cert_to_PEM_cert(intermediate)
    bundle = root_pem+intermediate_pem
    if (folder/'zalo-digicert-bundle.pem').read_text(encoding='ascii') != bundle:
        raise ValueError('bundle_bytes_mismatch')
    return root_pem, bundle, meta


def peer_summary(response):
    for candidate in (response, getattr(response, 'fp', None)):
        try:
            sock = candidate.fp.raw._sock
            der = sock.getpeercert(binary_form=True)
            info = sock.getpeercert()
            issuer = next((v for rdn in info.get('issuer', ()) for k,v in rdn if k=='commonName'), '')
            return {'leaf_sha256':sha256(der), 'issuer_matches_rapidssl':issuer=='RapidSSL TLS ECC CA G1'}
        except Exception:
            pass
    return {}


def probe(label, context, url=ZALO, opener=None):
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ValueError('verification_required')
    opener = opener or urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    try:
        with opener.open(url, timeout=20) as response:
            result = {'tls':'PASS','http':response.status,**peer_summary(response)}
    except urllib.error.HTTPError as error:
        if error.code == 407:
            result = {'tls':'FAIL','category':'PROXY_AUTH','proxy_http':407}
        else:
            result = {'tls':'PASS','http':error.code,**peer_summary(error)}
        error.close()
    except Exception as error:
        category, fields = classify(error)
        result = {'tls':'FAIL','category':category,**fields}
    print(label+'='+json.dumps(result, sort_keys=True))
    return result


def integration_check(bundle_path):
    # Only this diagnostic process changes environment, and always restores it.
    old = os.environ.get('SSL_CERT_FILE')
    try:
        os.environ['SSL_CERT_FILE'] = str(bundle_path.resolve())
        context = ssl.create_default_context()
        z = probe('JAT_DEFAULT_CONTEXT_WITH_PROCESS_CA',context)
        g = probe('GOOGLE_DEFAULT_CONTEXT_WITH_PROCESS_CA',context,GOOGLE)
        return z['tls']=='PASS' and g['tls']=='PASS'
    finally:
        if old is None:
            os.environ.pop('SSL_CERT_FILE',None)
        else:
            os.environ['SSL_CERT_FILE']=old


def main(offline=False):
    print('JAT DIGICERT CHECK v1 - NO TOKEN/KEY - NO WINDOWS STORE CHANGES')
    root_pem, bundle, meta = verified_files()
    print('ROOT_SHA256='+ROOT_SHA256)
    print('ROOT_SELF_SIGNATURE=PASS INTERMEDIATE_SIGNATURE=PASS CA_TIME=PASS')
    print('INTERMEDIATE_SHA256='+meta['intermediate_sha256'])
    print('REVOCATION=NOT_CHECKED (no CRL/OCSP claim; no checks disabled)')
    if offline:
        print('FILES_AND_SIGNATURES=PASS; no network request made')
        return 0
    baseline = None
    try:
        context = ssl.create_default_context()
        present = any(sha256(c)==ROOT_SHA256 for c in context.get_ca_certs(binary_form=True))
        print('ROOT_IN_DEFAULT_PYTHON_CA='+('YES' if present else 'NO'))
        baseline = probe('DEFAULT_ZALO',context)
    except Exception:
        print('DEFAULT_CONTEXT=UNAVAILABLE; no settings changed')
    root_result = probe('PRIVATE_ROOT_ONLY',make_context(root_pem))
    full_result = probe('PRIVATE_ROOT_PLUS_INTERMEDIATE',make_context(bundle))
    if full_result['tls']!='PASS':
        print('RESULT=FAIL; inspect category/code above. Do not add unknown CA or disable verification.')
        print('Codes 19/20/21 can mean another/unusable chain; compare actual route/issuer with IT.')
        print('Revocation was not checked here. If certutil reports revoked/offline CRL/OCSP, IT must resolve it; do not disable revocation.')
        return 1
    if root_result['tls']!='PASS':
        print('DIAGNOSIS=INTERMEDIATE_OR_CHAIN_SELECTION_ISSUE (full bundle passed, root-only did not)')
    elif baseline and baseline['tls']!='PASS':
        print('DIAGNOSIS=DEFAULT_TRUST_OR_CHAIN_ISSUE (pinned root-only passed)')
    else:
        print('DIAGNOSIS=TLS_PASS_IN_THIS_PROCESS')
    print('CHAIN_AND_HOSTNAME=PASS for the live verified connection; HTTP root status is not bot authorization.')
    integrated = integration_check(CA_DIR/'zalo-digicert-bundle.pem')
    print('PROCESS_ONLY_INTEGRATION_TEST='+('PASS' if integrated else 'FAIL'))
    print('No bot started. No setx, CA import, Windows policy, key vault or DB changes.')
    return 0 if integrated else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Pinned DigiCert G3 + RapidSSL CA TLS test')
    parser.add_argument('--verify-files',action='store_true',help='Offline CA fingerprints/signatures only')
    args=parser.parse_args()
    try:
        raise SystemExit(main(args.verify_files))
    except KeyboardInterrupt:
        print('Stopped; no trust settings changed.');raise SystemExit(130)
    except Exception as error:
        known = {'root_sha256_mismatch','root_pin_or_source_mismatch','root_identity_mismatch','intermediate_identity_mismatch','intermediate_source_invalid','intermediate_hash_mismatch','bundle_bytes_mismatch','ca_time_invalid_check_clock','root_signature_failed_or_crypto_unsupported','intermediate_signature_failed_or_crypto_unsupported','native_windows_required','certificate_decode_failed','tls_verification_not_enabled','partial_chain_not_allowed'}
        reason = str(error) if str(error) in known else 'missing_file_or_invalid_public_bundle_or_crypto'
        print('FILES_OR_CRYPTO=FAIL code='+reason)
        raise SystemExit(1)
