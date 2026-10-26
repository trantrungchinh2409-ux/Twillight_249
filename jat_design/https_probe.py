"""Credential-free TLS diagnostics with finite, safe error fields only."""
import re
import socket
import ssl
import urllib.error
import urllib.request
from .official_api import NoRedirect

TARGETS = (('Google', 'https://generativelanguage.googleapis.com/'),
           ('Zalo', 'https://bot-api.zaloplatforms.com/'))
REASONS = {'CERTIFICATE_VERIFY_FAILED', 'TLSV1_ALERT_PROTOCOL_VERSION',
           'TLSV1_ALERT_INTERNAL_ERROR', 'SSLV3_ALERT_HANDSHAKE_FAILURE',
           'TLSV1_ALERT_HANDSHAKE_FAILURE', 'WRONG_VERSION_NUMBER',
           'UNEXPECTED_EOF_WHILE_READING', 'EOF_OCCURRED_IN_VIOLATION_OF_PROTOCOL',
           'NO_SHARED_CIPHER', 'UNSUPPORTED_PROTOCOL', 'DH_KEY_TOO_SMALL',
           'CERTIFICATE_SIGNATURE_FAILURE', 'TLSV1_ALERT_ACCESS_DENIED'}


def error_fields(error):
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, ssl.SSLCertVerificationError):
        result = {'error': 'certificate_verification_failed'}
        code = getattr(reason, 'verify_code', None)
        if type(code) is int and 0 <= code <= 1000:
            result['certificate_code'] = code
        return result
    if isinstance(reason, ssl.SSLError):
        code = getattr(reason, 'reason', None)
        return {'error': 'tls_handshake_failed', 'tls_reason': code if code in REASONS else 'unclassified'}
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return {'error': 'timeout'}
    if isinstance(reason, socket.gaierror):
        return {'error': 'dns_failed'}
    # Proxy messages can contain credentials/URLs. Extract only the numeric status.
    if isinstance(reason, str):
        match = re.match(r'^Tunnel connection failed: ([1-5][0-9]{2})(?:\s|$)', reason)
        if match:
            return {'error': 'proxy_connect_rejected', 'proxy_http': int(match.group(1))}
    if isinstance(reason, OSError):
        result = {'error': 'network_failed'}
        code = getattr(reason, 'winerror', None) or getattr(reason, 'errno', None)
        if type(code) is int and -10000 <= code <= 100000:
            result['os_code'] = code
        return result
    return {'error': 'connection_failed'}


def check_https(output=print, opener=None):
    # Keep CA/hostname verification on. Do not use token-bearing paths or headers.
    context = ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        output('HTTPS: TLS verification unavailable; no request made.')
        return 1
    default_opener = opener or urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    output('TLS diagnostic v2; verification ON; no credentials or messages.')
    failures = 0
    for name, url in TARGETS:
        try:
            selected_opener = default_opener
            if name == 'Zalo' and opener is None:
                from .zalo_tls import configured_context
                zalo_context = configured_context()
                if zalo_context is not None:
                    selected_opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=zalo_context))
            with selected_opener.open(url, timeout=20) as response:
                code = response.status
            output('%s: HTTPS certificate validation passed, HTTP %s' % (name, code))
        except urllib.error.HTTPError as error:
            # A redirect is not followed; fixed origins contain no secrets.
            if error.code == 407:
                failures += 1
                output('%s: error=proxy_authentication_required proxy_http=407' % name)
            else:
                output('%s: HTTPS certificate validation passed, HTTP %s' % (name, error.code))
        except Exception as error:
            failures += 1
            fields = error_fields(error)
            output('%s: %s' % (name, ' '.join('%s=%s' % item for item in sorted(fields.items()))))
    output('No TLS, proxy, certificate or system settings were changed.')
    return 1 if failures else 0
