"""Read-only certificate/store comparison; optional IT-approved CA in this process only."""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
import check_zalo_tls as tls

BASE = Path(__file__).resolve().parent
SERVER_AUTH = '1.3.6.1.5.5.7.3.1'


def fingerprint(der):
    return hashlib.sha256(der).hexdigest().upper()


def store_snapshot(context):
    result = {'PYTHON': {fingerprint(c) for c in context.get_ca_certs(binary_form=True)}, 'ROOT': set(), 'CA': set(), 'ROOT_SERVER_AUTH': set(), 'CA_SERVER_AUTH': set()}
    if os.name == 'nt':
        for store in ('ROOT', 'CA'):
            for der, encoding, trust in ssl.enum_certificates(store):
                if encoding == 'x509_asn':
                    result[store].add(fingerprint(der))
                    if trust is True or SERVER_AUTH in trust:
                        result[store+'_SERVER_AUTH'].add(fingerprint(der))
    return result


def python_route():
    host = 'bot-api.zaloplatforms.com'
    if urllib.request.proxy_bypass(host):
        return 'DIRECT'
    proxy = urllib.request.getproxies().get('https')
    if not proxy:
        return 'DIRECT'
    p = urllib.parse.urlsplit(proxy if '://' in proxy else 'http://'+proxy)
    if not p.hostname:
        return 'UNKNOWN'
    return '%s://%s:%s' % (p.scheme.lower(), p.hostname.lower(), p.port or (443 if p.scheme.lower() == 'https' else 80))


def parse_windows_output(text):
    result = {'certificates': []}
    allowed = {'WINDOWS_HTTPS': {'PASS', 'FAIL', 'NOT_RUN'}, 'CHAIN_AVAILABLE': {'YES', 'NO'},
        'WINDOWS_CHAIN_VALID': {'YES', 'NO'}, 'WINDOWS_PROTOCOL': {'TLS12_PROCESS_ONLY'}}
    for line in text.splitlines():
        name, sep, value = line.partition('=')
        if not sep:
            continue
        if name in allowed and value in allowed[name]:
            result[name] = value
        elif name in ('WINDOWS_HTTP', 'CHAIN_STATUS_FLAGS') and re.fullmatch(r'[0-9]{1,10}', value):
            result[name] = int(value)
        elif name == 'WINDOWS_ERROR' and value in {'TrustFailure', 'SecureChannelFailure', 'Timeout', 'ConnectFailure', 'NameResolutionFailure', 'ProxyNameResolutionFailure', 'NONDEFAULT_CERT_VALIDATION_CALLBACK', 'SendFailure', 'ReceiveFailure', 'ConnectionClosed', 'UnknownError'}:
            result[name] = value
        elif name == 'WINDOWS_PROBE_ERROR':
            result[name] = 'UNAVAILABLE_POLICY_RUNTIME_OR_TLS12'
        elif name == 'ROUTE_B64':
            try:
                route = base64.b64decode(value, validate=True).decode('utf-8')
                result['ROUTE_MATCH'] = 'YES' if route != 'UNKNOWN' and route == python_route() else 'NO_OR_UNKNOWN'
            except Exception:
                result['ROUTE_MATCH'] = 'NO_OR_UNKNOWN'
        elif name == 'LEAF_DER' or re.fullmatch(r'CERT_[0-9]{1,2}_DER', name):
            try:
                der = base64.b64decode(value, validate=True)
                if 0 < len(der) <= 65536:
                    if name == 'LEAF_DER':
                        result['LEAF_SHA256'] = fingerprint(der)
                    elif len(result['certificates']) < 16:
                        result['certificates'].append(fingerprint(der))
            except Exception:
                pass
    return result


def windows_probe():
    if os.name != 'nt':
        return {'WINDOWS_PROBE_ERROR': 'WINDOWS_REQUIRED', 'certificates': []}
    executable = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    try:
        r = subprocess.run([str(executable), '-NoProfile', '-NonInteractive', '-File', os.path.join(str(BASE), 'inspect_zalo_windows_chain.ps1')],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    except subprocess.TimeoutExpired:
        return {'WINDOWS_PROBE_ERROR': 'TIMEOUT', 'certificates': []}
    except Exception:
        return {'WINDOWS_PROBE_ERROR': 'UNAVAILABLE', 'certificates': []}
    result = parse_windows_output(r.stdout.decode('ascii', errors='replace'))
    if r.returncode and not result.get('WINDOWS_PROBE_ERROR'):
        # Do not print PowerShell stderr (may contain usernames/paths/company policy).
        result['WINDOWS_PROBE_ERROR'] = 'POWERSHELL_POLICY_OR_RUNTIME_BLOCKED'
    return result


def tlv(data, at=0):
    if at+2 > len(data):
        raise ValueError('Invalid DER')
    tag, length = data[at], data[at+1]
    pos = at+2
    if length & 128:
        count = length & 127
        if not 1 <= count <= 4 or pos+count > len(data):
            raise ValueError('Invalid DER length')
        length = int.from_bytes(data[pos:pos+count], 'big'); pos += count
    end = pos+length
    if end > len(data):
        raise ValueError('Truncated DER')
    return tag, data[pos:end], end


def children(data):
    at = 0
    while at < len(data):
        tag, value, at = tlv(data, at)
        yield tag, value


def is_ca(der):
    # Parse only CA/keyCertSign extensions, not a custom signature verifier.
    # Cryptographic/hostname verification remains OpenSSL's responsibility.
    tag, certificate, end = tlv(der)
    if tag != 48 or end != len(der):
        return False
    tag, tbs, _ = tlv(certificate)
    if tag != 48:
        return False
    ca, usage_ok, seen = False, True, set()
    for tag, extensions in children(tbs):
        if tag != 163:
            continue
        tag, encoded, end = tlv(extensions)
        if tag != 48 or end != len(extensions):
            return False
        for tag, extension in children(encoded):
            fields = list(children(extension))
            if tag != 48 or len(fields) not in (2, 3) or fields[0][0] != 6 or fields[-1][0] != 4:
                return False
            oid = fields[0][1]
            if oid in seen:
                return False
            seen.add(oid)
            if oid == b'\x55\x1d\x13':
                tag, constraints, end = tlv(fields[-1][1])
                values = list(children(constraints))
                ca = tag == 48 and end == len(fields[-1][1]) and bool(values) and values[0] == (1, b'\xff')
            elif oid == b'\x55\x1d\x0f':
                tag, bits, end = tlv(fields[-1][1])
                usage_ok = tag == 3 and len(bits) >= 2 and bits[0] <= 7 and bool(bits[1] & 4) and end == len(fields[-1][1])
    return ca and usage_ok


def approved_context(context_factory, path, expected):
    expected = re.sub(r'[:\s]', '', expected).upper()
    if not re.fullmatch(r'[A-F0-9]{64}', expected):
        raise ValueError('IT fingerprint required')
    if path.stat().st_size > 65536:
        raise ValueError('CA file too large')
    raw = path.read_bytes()
    if raw.strip().startswith(b'-----BEGIN'):
        match = re.fullmatch(rb'\s*-----BEGIN CERTIFICATE-----\s*([A-Za-z0-9+/=\s]+?)\s*-----END CERTIFICATE-----\s*', raw)
        if not match:
            raise ValueError('One public CA certificate only')
        der = base64.b64decode(b''.join(match[1].split()), validate=True)
    else:
        der = raw
    if fingerprint(der) != expected or not is_ca(der):
        raise ValueError('CA fingerprint mismatch or not CA')
    context = context_factory()
    flags = context.verify_flags
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ValueError('Verification required')
    context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der))
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname or context.verify_flags != flags:
        raise ValueError('Verification changed')
    return context, expected


def main():
    print('JAT ZALO CERT CHECK v2 - READ ONLY - NO TOKEN/KEY - NO SSL BYPASS')
    context = ssl.create_default_context()
    try:
        stores = store_snapshot(context)
        print('WINDOWS_STORE_READ=%s' % ('PASS' if os.name == 'nt' else 'NOT_WINDOWS'))
    except Exception:
        stores = {'PYTHON': {fingerprint(c) for c in context.get_ca_certs(binary_form=True)}, 'ROOT': set(), 'CA': set(), 'ROOT_SERVER_AUTH': set(), 'CA_SERVER_AUTH': set()}
        print('WINDOWS_STORE_READ=FAIL; zero counts do not prove stores are empty')
    print('PYTHON_CA_COUNT=%s WINDOWS_ROOT_COUNT=%s WINDOWS_CA_COUNT=%s' % tuple(len(stores[k]) for k in ('PYTHON', 'ROOT', 'CA')))
    print('CPython 3.8 default context loads Windows ROOT/CA for server-auth plus OpenSSL defaults; not certifi.')
    print('CA_OVERRIDE_CONFIGURED=%s' % ('YES' if os.environ.get('SSL_CERT_FILE') or os.environ.get('SSL_CERT_DIR') else 'NO'))
    opener = urllib.request.build_opener(tls.NoRedirect(), urllib.request.HTTPSHandler(context=context))
    default_pass = tls.probe('Zalo PYTHON_DEFAULT', 'bot-api.zaloplatforms.com', opener)
    windows = windows_probe()
    for key in sorted(windows):
        if key != 'certificates':
            print('%s=%s' % (key, windows[key]))
    if 'CHAIN_STATUS_FLAGS' in windows:
        flags = windows['CHAIN_STATUS_FLAGS']
        meanings = [(1, 'NotTimeValid'), (4, 'Revoked'), (16, 'NotValidForUsage'), (32, 'UntrustedRoot'), (64, 'RevocationStatusUnknown'), (65536, 'PartialChain'), (16777216, 'OfflineRevocation'), (67108864, 'ExplicitDistrust')]
        print('WINDOWS_CHAIN_STATUS=%s' % (','.join(name for bit, name in meanings if flags & bit) or ('NoError' if not flags else 'OtherFlags')))
    print('CHAIN_SOURCE=Windows_built_from_ServicePoint_certificate_not_wire_chain')
    print('Windows/.NET may use PAC/different route; compare ROUTE_MATCH before attributing differences to trust stores.')
    for index, sha in enumerate(windows['certificates']):
        print('CHAIN_%s_SHA256=%s IN_WINDOWS_ROOT=%s IN_WINDOWS_CA=%s IN_PYTHON_CA=%s WINDOWS_SERVER_AUTH_ELIGIBLE=%s' % (
            index, sha, 'YES' if sha in stores['ROOT'] else 'NO', 'YES' if sha in stores['CA'] else 'NO', 'YES' if sha in stores['PYTHON'] else 'NO', 'YES' if sha in (stores['ROOT_SERVER_AUTH'] | stores['CA_SERVER_AUTH']) else 'NO'))
    if not windows['certificates']:
        print('CHAIN=UNAVAILABLE; no unverified TLS fallback. Use browser certificate viewer/IT, do not proceed past browser warnings.')
    path = BASE/'APPROVED_CA.pem'
    approved_pass = None
    blocked = bool(windows.get('CHAIN_STATUS_FLAGS', 0) & ~(32 | 65536))
    if path.exists() and blocked:
        print('APPROVED_CA_TEST=NOT_RUN: Windows reports non-trust/partial-chain errors; resolve with IT, do not override.')
    elif path.exists():
        print('Optional IT-approved PUBLIC CA found. No trust added automatically.')
        expected = input('Only IT-approved HTTPS CA: paste independently verified SHA256 (or Enter to skip): ').strip()
        if expected:
            try:
                extra, sha = approved_context(ssl.create_default_context, path, expected)
                print('APPROVED_CA_IN_WINDOWS_ROOT=%s IN_PYTHON_DEFAULT=%s IN_WINDOWS_CHAIN=%s' % (
                    'YES' if sha in stores['ROOT'] else 'NO', 'YES' if sha in stores['PYTHON'] else 'NO', 'YES' if sha in windows['certificates'] else 'NO'))
                opener = urllib.request.build_opener(tls.NoRedirect(), urllib.request.HTTPSHandler(context=extra))
                approved_pass = tls.probe('Zalo APPROVED_CA_PROCESS_ONLY', 'bot-api.zaloplatforms.com', opener)
            except Exception:
                print('APPROVED_CA_TEST=NOT_RUN: approval fingerprint/CA file/validation check failed; no trust changed.')
    else:
        print('APPROVED_CA_TEST=NOT_RUN: ask IT for public root CA and SHA256 via an independent approved channel.')
    print('PYTHON_DEFAULT_RESULT=%s APPROVED_CA_RESULT=%s' % ('PASS' if default_pass else 'FAIL', 'NOT_RUN' if approved_pass is None else 'PASS' if approved_pass else 'FAIL'))
    print('Certificate 19 alone does not prove interception. IT must identify issuer/root and compare approved SHA256.')
    print('No Windows certificate imported, no security policy changed, no bot files/DB read. HTTPS bodies not read.')
    return 0 if default_pass else 2 if approved_pass else 1


if __name__ == '__main__':
    argparse.ArgumentParser(description='Read-only Windows/Python certificate chain check; no credentials').parse_args()
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Stopped; no security settings changed.'); raise SystemExit(130)
    except Exception:
        print('CERT_CHECK=FAIL LOCAL_DIAGNOSTIC; details hidden, no trust changed.'); raise SystemExit(1)
