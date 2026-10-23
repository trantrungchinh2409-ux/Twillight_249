"""Persistent deduplication. No token, message text or API response is stored."""
import sqlite3


class State:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.execute('CREATE TABLE IF NOT EXISTS deliveries ('
                        'chat_id TEXT, event_id TEXT, status TEXT NOT NULL, '
                        'PRIMARY KEY(chat_id, event_id))')
        self.db.commit()

    def reserve(self, chat_id, event_id):
        with self.db:
            cursor = self.db.execute(
                'INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?)',
                (chat_id, event_id, 'reserved'))
        return cursor.rowcount == 1

    def mark(self, chat_id, event_id, status):
        with self.db:
            self.db.execute('UPDATE deliveries SET status=? '
                            'WHERE chat_id=? AND event_id=?',
                            (status, chat_id, event_id))

    def close(self):
        self.db.close()
