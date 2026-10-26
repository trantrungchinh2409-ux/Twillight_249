"""Standalone read-only Win7 TLS check. No bot imports, credentials or policy changes."""
import argparse
from datetime import datetime, timezone
import os
import queue
import re
import socket
import ssl
import sys
import threading
import urllib.error
import urllib.request

TARGETS = (('Google', 'generativelanguage.googleapis.com'), ('Zalo', 'bot-api.zaloplatforms.com'))
TLS_REASONS = {'CERTIFICATE_VERIFY_FAILED', 'TLSV1_ALERT_PROTOCOL_VERSION',
    'SSLV3_ALERT_HANDSHAKE_FAILURE', 'TLSV1_ALERT_HANDSHAKE_FAILURE', 'WRONG_VERSION_NUMBER',
    'TLSV1_ALERT_INTERNAL_ERROR', 'UNEXPECTED_EOF_WHILE_READING', 'NO_SHARED_CIPHER',
    'UNSUPPORTED_PROTOCOL', 'DH_KEY_TOO_SMALL', 'TLSV1_ALERT_ACCESS_DENIED',
    'EOF_OCCURRED_IN_VIOLATION_OF_PROTOCOL'}
CERT_CODES = {9: 'certificate_not_yet_valid_or_clock', 10: 'certificate_expired_or_clock',
    18: 'self_signed_certificate', 19: 'self_signed_certificate_in_chain',
    20: 'issuer_not_trusted_or_chain_incomplete', 21: 'unable_to_verify_certificate_chain',
    62: 'certificate_hostname_mismatch'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def classify(error):
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, ssl.SSLCertVerificationError):
        code = getattr(reason, 'verify_code', None)
        safe_code = code if type(code) is int and 0 <= code <= 1000 else 'unknown'
        return 'CERTIFICATE', {'certificate_code': safe_code, 'cause': CERT_CODES.get(safe_code, 'certificate_verification_failed')}
    if isinstance(reason, ssl.SSLError):
        code = getattr(reason, 'reason', None)
        return 'TLS_HANDSHAKE', {'tls_reason': code if code in TLS_REASONS else 'unclassified'}
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return 'TIMEOUT', {'cause': 'server_or_network_no_response_source_unknown'}
    if isinstance(reason, socket.gaierror):
        return 'DNS', {'cause': 'resolver_failed_source_unknown'}
    if isinstance(reason, str):
        m = re.match(r'^Tunnel connection failed: ([1-5][0-9]{2})(?:\s|$)', reason)
        if m:
            return 'PROXY_CONNECT', {'proxy_http': int(m.group(1)), 'cause': 'proxy_rejected_tunnel'}
    if isinstance(reason, OSError):
        code = getattr(reason, 'winerror', None) or getattr(reason, 'errno', None)
        return 'NETWORK', {'os_code': code if type(code) is int and -10000 <= code <= 100000 else 'unknown', 'cause': 'network_error_source_unknown'}
    return 'UNKNOWN', {'cause': 'connection_failed_no_private_details_printed'}


def dns_status(host, timeout=5):
    result = queue.Queue(maxsize=1)
    def lookup():
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            result.put('PASS')
        except Exception:
            result.put('FAIL')
    worker = threading.Thread(target=lookup, daemon=True)
    worker.start()
    try:
        return result.get(timeout=timeout)
    except queue.Empty:
        return 'TIMEOUT'


def probe(name, host, opener, output=print):
    try:
        with opener.open('https://'+host+'/', timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        if status == 407:
            output('[%s] HTTPS=FAIL category=PROXY_AUTH proxy_http=407' % name)
            return False
    except Exception as error:
        category, fields = classify(error)
        output('[%s] HTTPS=FAIL category=%s %s' % (name, category,
            ' '.join('%s=%s' % item for item in sorted(fields.items()))))
        return False
    output('[%s] HTTPS=PASS certificate=verified HTTP=%s' % (name, status))
    if status in (401, 403, 451):
        output('[%s] HTTP_ACCESS=REJECTED source_unknown; TLS passed, bot authorization not tested.' % name)
    return True


def pac_status():
    if os.name != 'nt':
        return 'NOT_WINDOWS'
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            try:
                value, _ = winreg.QueryValueEx(key, 'AutoConfigURL')
                return 'YES' if bool(value) else 'NO'
            except FileNotFoundError:
                return 'NO'
    except Exception:
        return 'UNKNOWN'


def run(output=print):
    output('JAT ZALO TLS CHECK v1 - READ ONLY - NO BOT TOKEN / NO GEMINI KEY')
    output('Python=%s OpenSSL=%s UTC_CLOCK=%s' % (sys.version.split()[0], ssl.OPENSSL_VERSION, datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    proxies = urllib.request.getproxies()
    output('PROXY_CONFIGURED=%s (address/credentials hidden)' % ('YES' if proxies.get('https') or proxies.get('all') else 'NO'))
    output('PAC_CONFIGURED=%s (URL hidden; Python urllib does not execute PAC)' % pac_status())
    output('CA_OVERRIDE_CONFIGURED=%s' % ('YES' if any(os.environ.get(k) for k in ('SSL_CERT_FILE', 'SSL_CERT_DIR')) else 'NO'))
    try:
        context = ssl.create_default_context()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            output('RESULT=FAIL category=TLS_VERIFICATION_UNAVAILABLE; no request made')
            return 1
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    except Exception:
        output('RESULT=FAIL category=TLS_CONTEXT; no private details printed')
        return 1
    results = {}
    for name, host in TARGETS:
        output('[%s] LOCAL_DNS=%s (a configured proxy may resolve remotely)' % (name, dns_status(host)))
        results[name] = probe(name, host, opener, output)
    output('ZALO_TLS_RESULT=%s GOOGLE_CONTROL=%s' % ('PASS' if results['Zalo'] else 'FAIL', 'PASS' if results['Google'] else 'FAIL'))
    output('HTTP 404 at origin root can be TLS PASS. No API auth or chat messages tested.')
    output('Only explicit PROXY_CONNECT/PROXY_AUTH identifies a proxy refusal. Timeout/reset/DNS alone does not prove company blocking.')
    output('No SSL, CA, proxy, Windows security, bot files or database settings were changed.')
    return 0 if results['Zalo'] else 1


if __name__ == '__main__':
    argparse.ArgumentParser(description='Read-only Google/Zalo TLS diagnostics, no credentials required').parse_args()
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print('Stopped; no settings changed.')
        raise SystemExit(130)
    except Exception:
        print('RESULT=FAIL category=LOCAL_DIAGNOSTIC; no private details printed')
        raise SystemExit(1)
