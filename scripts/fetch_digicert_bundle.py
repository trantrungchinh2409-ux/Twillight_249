"""Build public certificate files from official DigiCert HTTPS only, with pinned root."""
from html.parser import HTMLParser
import json
from pathlib import Path
import ssl
import sys
import urllib.parse
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from digicert_bundle import ROOT_URL, ROOT_SHA256, ROOT_CN, INTERMEDIATE_CN, certificate_der, describe, sha256, validate_public_cas

EVENTS = []
STAGE = 'root_download'


def record(error):
    safe = {'stage': STAGE, 'type': type(error).__name__}
    if isinstance(error, urllib.error.HTTPError):
        safe['http_status'] = error.code
    known = {'root_sha256_mismatch', 'root_identity_mismatch', 'intermediate_identity_mismatch',
        'ca_time_invalid_check_clock', 'root_signature_failed_or_crypto_unsupported',
        'intermediate_signature_failed_or_crypto_unsupported', 'official_intermediate_not_verified',
        'certificate_decode_failed', 'certificate_format_invalid', 'download_limit'}
    if str(error) in known:
        safe['code'] = str(error)
    EVENTS.append(safe)


HOSTS = {'cacerts.digicert.com', 'www.digicert.com', 'knowledge.digicert.com'}


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None,443) or p.username or p.password:
        raise ValueError('non_official_https_url')


def download(url, limit=65536):
    validate_url(url)
    opener = urllib.request.build_opener(OfficialRedirect())
    with opener.open(url, timeout=30) as r:
        validate_url(r.url)
        data = r.read(limit+1)
    if len(data) > limit:
        raise ValueError('download_limit')
    return data


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attributes):
        if tag == 'a':
            href = dict(attributes).get('href', '')
            if 'rapidssl' in href.lower() and 'ecc' in href.lower():
                self.links.append(href)


def main():
    global STAGE
    root = certificate_der(download(ROOT_URL))
    if sha256(root) != ROOT_SHA256:
        raise ValueError('root_sha256_mismatch')
    # Official-host candidates are accepted only after subject/issuer/signature validation.
    candidates = ['https://cacerts.digicert.com/RapidSSLTLSECCCAG1.crt']
    pages = ['https://www.digicert.com/kb/digicert-root-certificates.htm',
             'https://www.digicert.com/kb/digicert-intermediate-certificates.htm']
    found, source, descriptions = None, None, None
    STAGE = 'intermediate_candidate'
    for url in candidates:
        try:
            data = certificate_der(download(url))
            descriptions = validate_public_cas(root, data)
            found, source = data, url
            break
        except Exception as error:
            record(error)
            print('Official intermediate candidate not accepted; trying official catalog.')
    if found is None:
        STAGE = 'official_catalog'
        for page in pages:
            try:
                parser = Links(); parser.feed(download(page, 2_000_000).decode('utf-8', errors='replace'))
                for href in parser.links:
                    url = urllib.parse.urljoin(page, href)
                    url = urllib.parse.quote(url, safe=':/%?=&')
                    if urllib.parse.urlsplit(url).hostname == 'cacerts.digicert.com':
                        candidates.append(url)
            except Exception as error:
                record(error)
                print('Official catalog unavailable; no verification disabled.')
        STAGE = 'catalog_certificate'
        for url in list(dict.fromkeys(candidates))[1:21]:
            try:
                data = certificate_der(download(url))
                descriptions = validate_public_cas(root, data)
                found, source = data, url
                break
            except Exception as error:
                record(error)
    if found is None:
        raise ValueError('official_intermediate_not_verified')
    folder = ROOT/'ca_digicert'; folder.mkdir(exist_ok=True)
    root_pem, int_pem = ssl.DER_cert_to_PEM_cert(root), ssl.DER_cert_to_PEM_cert(found)
    (folder/'DigiCertGlobalRootG3.pem').write_text(root_pem, encoding='ascii')
    (folder/'RapidSSLTLSECCCAG1.pem').write_text(int_pem, encoding='ascii')
    (folder/'zalo-digicert-bundle.pem').write_text(root_pem+int_pem, encoding='ascii')
    metadata = {'root_sha256':ROOT_SHA256, 'root_source':ROOT_URL, 'root':descriptions[0],
        'intermediate_sha256':sha256(found), 'intermediate_source':source, 'intermediate':descriptions[1],
        'root_self_signature_verified':True, 'intermediate_signature_verified':True,
        'revocation_checked':False, 'source':'official DigiCert HTTPS; no mirror or insecure TLS'}
    (folder/'SOURCE.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print('ROOT_SHA256='+ROOT_SHA256)
    print('INTERMEDIATE_SHA256='+sha256(found))
    print('ROOT_SELF_SIGNATURE=PASS INTERMEDIATE_SIGNATURE=PASS SOURCES=OFFICIAL_DIGICERT_HTTPS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        record(error)
        folder = ROOT/'ca_digicert'; folder.mkdir(exist_ok=True)
        (folder/'BUILD_STATUS.json').write_text(json.dumps({'status':'FAIL', 'events':EVENTS}, indent=2)+'\n', encoding='utf-8')
        print('OFFICIAL_BUNDLE=FAIL; see safe BUILD_STATUS.json')
        raise SystemExit(1)
