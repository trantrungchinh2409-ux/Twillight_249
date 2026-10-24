"""User-scoped DPAPI store. No plaintext disk files, key previews or secret logs."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import time
from .gemini_client import Gemini, GeminiError, PREFERRED
from .webhook_switch import protect, RUNTIME

VAULT_PATH = RUNTIME/'gemini_keys.dpapi'
VAULT_LOCK = 'JAT-Design-Gemini-Vault-Exclusive'
KEY_REASONS = {'API_KEY_INVALID', 'API_KEY_EXPIRED', 'API_KEY_REVOKED',
               'API_KEY_SERVICE_BLOCKED', 'API_KEY_IP_ADDRESS_BLOCKED',
               'API_KEY_HTTP_REFERRER_BLOCKED'}


def key_specific(error):
    return (isinstance(error, GeminiError) and error.code not in (402, 429)
            and error.reason not in ('BILLING_DISABLED', 'BILLING_NOT_ACTIVE', 'PROJECT_BILLING_DISABLED')
            and (error.code == 401 or error.reason in KEY_REASONS))


def error_label(error):
    if error.code == 429: return 'quota_wait'
    if key_specific(error): return 'invalid_key'
    if error.code == 402 or error.reason in ('BILLING_DISABLED', 'BILLING_NOT_ACTIVE', 'PROJECT_BILLING_DISABLED'):
        return 'billing_problem'
    return 'provider_error'


class Vault:
    def __init__(self, path=VAULT_PATH):
        self.path = Path(path)
        self.data = {'version': 1, 'primary': None, 'items': [], 'wait_until': 0, 'quota_errors': 0, 'active': None}
        if self.path.exists():
            loaded = json.loads(protect(self.path.read_bytes(), decrypt=True).decode('utf-8'))
            if loaded.get('version') != 1 or not isinstance(loaded.get('items'), list):
                raise ValueError('Invalid vault')
            ids = set()
            for item in loaded['items']:
                if (not isinstance(item, dict) or not isinstance(item.get('key'), str)
                        or not item['key'].strip() or item.get('id') in ids):
                    raise ValueError('Invalid vault entry')
                ids.add(item['id'])
            if loaded['items'] and loaded.get('primary') not in ids:
                raise ValueError('Invalid primary')
            self.data = loaded

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(self.data, ensure_ascii=False).encode('utf-8')
        encoded = protect(raw)
        temp = self.path.with_name(self.path.name+'.'+secrets.token_hex(8)+'.tmp')
        try:
            with temp.open('xb') as file:
                file.write(encoded); file.flush(); os.fsync(file.fileno())
            if protect(temp.read_bytes(), decrypt=True) != raw:
                raise OSError('Vault readback failed')
            os.replace(temp, self.path)
        finally:
            if temp.exists(): temp.unlink()

    def add(self, key):
        key = key.strip()
        if not key or any(c.isspace() for c in key): raise ValueError('Invalid key input')
        if any(item['key'] == key for item in self.data['items']): return False
        item = {'id': secrets.token_hex(6), 'key': key, 'status': 'not_checked', 'checked_at': None}
        self.data['items'].append(item)
        if self.data['primary'] is None: self.data['primary'] = item['id']
        self.save()
        return True

    def remove(self, index):
        old = self.data['items'].pop(index)
        if self.data.get('active') == old['id']: self.data['active'] = None
        if self.data['primary'] == old['id']:
            self.data['primary'] = self.data['items'][0]['id'] if self.data['items'] else None
        self.save()

    def primary(self, index):
        self.data['primary'] = self.data['items'][index]['id']
        self.data['active'] = self.data['primary']
        self.save()

    def ordered(self):
        return sorted(self.data['items'], key=lambda item: item['id'] != self.data['primary'])

    def mark(self, item, status, code=None):
        item['status'], item['code'] = status, code
        item['checked_at'] = datetime.now(timezone.utc).isoformat()
        self.save()

    def wait_remaining(self, now=None):
        return max(0, self.data.get('wait_until', 0)-(time.time() if now is None else now))

    def quota_wait(self, error, now=None):
        now = time.time() if now is None else now
        count = self.data.get('quota_errors', 0)+1
        delay = error.retry_after if error.retry_after is not None else min(3600, 60*2**min(count-1, 6))
        self.data['wait_until'] = max(self.data.get('wait_until', 0), now+max(1, delay))
        self.data['quota_errors'] = count
        self.save()


class KeyPool:
    def __init__(self, vault, prompt, factory=Gemini, output=print):
        self.vault, self.prompt, self.factory, self.output = vault, prompt, factory, output
        self.model = PREFERRED[0]
        self.active = vault.data.get('active') or vault.data['primary']
        self.last_good = vault.data.get('last_good') or vault.data['primary']

    def wait_remaining(self): return self.vault.wait_remaining()

    def status(self):
        items = self.vault.data['items']
        active = next((i for i, item in enumerate(items, 1) if item['id'] == self.active), None)
        return {'active': active, 'active_status': items[active-1].get('status', 'not_checked') if active else 'none',
                'keys': [{'number': i, 'primary': item['id'] == self.vault.data['primary'],
                          'status': item.get('status', 'not_checked')}
                         for i, item in enumerate(items, 1)]}

    def generate(self, question):
        remaining = self.wait_remaining()
        if remaining > 0:
            raise GeminiError('Provider waiting; no request made', 429, 'api', retry_after=remaining)
        ordered = self.vault.ordered()
        ordered.sort(key=lambda item: item['id'] != self.active)
        for item in ordered:
            if item.get('status') == 'invalid_key': continue
            self.active = item['id']
            if self.vault.data.get('active') != self.active:
                self.vault.data['active'] = self.active
                self.vault.save()
            client = self.factory(item['key'], self.prompt)
            client.model = self.model
            try:
                answer = client.generate(question)
            except GeminiError as error:
                label = error_label(error)
                self.vault.mark(item, label, error.code)
                if error.code == 429:
                    self.vault.quota_wait(error)
                    raise  # No alternate key/account for quota.
                if key_specific(error):
                    self.output('Khóa có lỗi riêng đã xác định; kiểm tra khóa dự phòng đã lưu.')
                    continue
                raise  # Billing, permissions, model, network: no key rotation.
            self.vault.data['last_good'] = item['id']
            self.vault.mark(item, 'generation_verified')
            if self.last_good != item['id'] and item['id'] != self.vault.data['primary']:
                number = self.vault.data['items'].index(item)+1
                self.output('Đã chuyển sang API dự phòng #%s' % number)
            self.last_good = item['id']
            if self.vault.data.get('quota_errors', 0):
                self.vault.data['quota_errors'] = 0; self.vault.save()
            return answer
        raise GeminiError('No usable saved key; open SETUP_API', 401, 'api', reason='API_KEY_INVALID')
