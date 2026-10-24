"""Persistent shared AI window, separate Google waits, durable Zalo send guards."""
import time
from .auto_reply import TRIGGER, hashed
from .gemini_client import GeminiError
from .key_vault import error_label

NOTICE = 'JAT Design đã hết lượt sử dụng tạm thời. Vui lòng thử lại sau 5 phút.'


class ManagedResponder:
    def __init__(self, state, bot_id, group_id, clock=time.time):
        self.state, self.bot_id, self.group_id, self.clock = state, bot_id, group_id, clock
        self.bot_key, self.group_key = hashed(bot_id), hashed(bot_id+'\0'+group_id)
        self.last_error = None
        db = state.db
        db.execute('CREATE TABLE IF NOT EXISTS ai_window_calls (bot TEXT NOT NULL, t REAL NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS ai_window_time ON ai_window_calls(bot,t)')
        db.execute('CREATE TABLE IF NOT EXISTS ai_window_state (bot TEXT PRIMARY KEY, local_until REAL NOT NULL, notified INTEGER NOT NULL, google_until REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS auto_limits (k TEXT PRIMARY KEY, next_at REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS auto_block (k TEXT PRIMARY KEY, reason TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO ai_window_state VALUES (?,0,0,0)', (self.bot_key,))
        db.commit()

    def blocked(self):
        return self.state.db.execute('SELECT 1 FROM auto_block WHERE k=?', (self.bot_key,)).fetchone() is not None

    def status(self):
        now, db = self.clock(), self.state.db
        row = db.execute('SELECT local_until,notified,google_until FROM ai_window_state WHERE bot=?', (self.bot_key,)).fetchone()
        times = [r[0] for r in db.execute('SELECT t FROM ai_window_calls WHERE bot=? AND t>?', (self.bot_key, now-120))]
        cooldown = db.execute('SELECT next_at FROM auto_limits WHERE k=?', (self.group_key,)).fetchone()
        return {'remaining': 0 if row[0] > now else max(0, 10-len(times)),
                'local_until': row[0], 'google_until': row[2], 'notice_reserved': bool(row[1]),
                'cooldown_until': cooldown[0] if cooldown else 0, 'window_times': times,
                'uncertain': self.blocked()}

    def _claim_ai(self):
        now, db = self.clock(), self.state.db
        with db:
            row = db.execute('SELECT local_until FROM ai_window_state WHERE bot=?', (self.bot_key,)).fetchone()
            if row[0] > now: return False
            db.execute('DELETE FROM ai_window_calls WHERE bot=? AND t<=?', (self.bot_key, now-120))
            count = db.execute('SELECT count(*) FROM ai_window_calls WHERE bot=?', (self.bot_key,)).fetchone()[0]
            if count >= 10:
                db.execute('UPDATE ai_window_state SET local_until=?,notified=0 WHERE bot=?', (now+300, self.bot_key))
                return False
            db.execute('INSERT INTO ai_window_calls VALUES (?,?)', (self.bot_key, now))
            if count+1 >= 10:
                db.execute('UPDATE ai_window_state SET local_until=?,notified=0 WHERE bot=?', (now+300, self.bot_key))
        return True

    def _mark(self, key, status):
        self.state.mark(self.group_key, key, status)
        return status

    def _send(self, api, text, key, still_on, notice=False):
        if not still_on(): return self._mark(key, 'off')
        now, db = self.clock(), self.state.db
        with db:
            if notice:
                db.execute('UPDATE ai_window_state SET notified=1 WHERE bot=?', (self.bot_key,))
            db.execute('INSERT INTO auto_block VALUES (?,?)', (self.bot_key, 'send_pending_or_uncertain'))
            db.execute('INSERT OR REPLACE INTO auto_limits VALUES (?,?)', (self.group_key, now+10))
        try:
            ack = api.sendMessage(self.group_id, text)
            if not isinstance(ack, dict) or not isinstance(ack.get('message_id'), str) or not ack['message_id']:
                raise RuntimeError('No send acknowledgement')
        except Exception as error:
            self.last_error = {'source': 'zalo', 'kind': getattr(error, 'kind', 'unknown'), 'code': getattr(error, 'code', None)}
            return self._mark(key, 'uncertain_blocked')
        self._mark(key, 'api_acknowledged_notice' if notice else 'api_acknowledged')
        with db: db.execute('DELETE FROM auto_block WHERE k=?', (self.bot_key,))
        return 'notice_sent' if notice else 'sent'

    def handle(self, api, pool, event, enabled, armed_ms, still_on=lambda: True):
        self.last_error = None
        if not enabled: return 'off'
        if self.blocked(): return 'uncertain_blocked'
        if not isinstance(event, dict) or event.get('event_name') != 'message.text.received': return 'ignored'
        m = event.get('message')
        if not isinstance(m, dict): return 'ignored'
        chat, sender = m.get('chat'), m.get('from')
        if not isinstance(chat, dict) or not isinstance(sender, dict): return 'ignored'
        if (chat.get('chat_type') != 'GROUP' or chat.get('id') != self.group_id
                or sender.get('is_bot') is not False or not isinstance(sender.get('id'), str)
                or not sender['id'].strip() or sender['id'] == self.bot_id
                or not isinstance(m.get('text'), str) or TRIGGER not in m['text']
                or not isinstance(m.get('message_id'), str) or not m['message_id'].strip()): return 'ignored'
        stamp, now = m.get('date'), self.clock()
        if type(stamp) not in (int, float) or not armed_ms <= stamp <= now*1000+60000: return 'old_or_unknown_time'
        question = m['text'].replace(TRIGGER, '', 1).strip()
        if not question: return 'empty_question'
        key = hashed(m['message_id'])
        if not self.state.reserve(self.group_key, key): return 'duplicate'
        info = self.status()
        if info['cooldown_until'] > now: return self._mark(key, 'cooldown')
        if info['local_until'] > now:
            if info['notice_reserved']: return self._mark(key, 'internal_wait')
            return self._send(api, NOTICE, key, still_on, notice=True)
        if max(info['google_until'], now+pool.wait_remaining()) > now:
            return self._mark(key, 'google_wait')
        if not still_on(): return self._mark(key, 'off')
        if not self._claim_ai():
            return self._mark(key, 'internal_wait')
        # Throttle Gemini attempts too, even when no Zalo response is produced.
        with self.state.db:
            self.state.db.execute('INSERT OR REPLACE INTO auto_limits VALUES (?,?)', (self.group_key, now+10))
        try:
            answer = pool.generate(question)
        except GeminiError as error:
            label = error_label(error)
            self.last_error = {'source': 'gemini', 'category': label, 'kind': error.kind,
                               'code': error.code, 'reason': error.reason}
            if error.code == 429:
                delay = error.retry_after if error.retry_after is not None else 60
                until = max(self.clock()+max(1, delay), self.clock()+pool.wait_remaining())
                with self.state.db:
                    self.state.db.execute('UPDATE ai_window_state SET google_until=max(google_until,?) WHERE bot=?', (until, self.bot_key))
                return self._mark(key, 'google_wait')
            return self._mark(key, label)
        return self._send(api, answer, key, still_on)
