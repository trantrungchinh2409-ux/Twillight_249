"""Offline test double. Never calls Zalo; not an official response fixture."""
from collections import deque
from .core import Event


class MockAPI:
    def __init__(self, events):
        self.events = deque(events)
        self.sent = []

    def getUpdates(self):
        return self.events.popleft() if self.events else None

    def sendMessage(self, chat_id, text):
        self.sent.append((chat_id, text))


def scenario(bot_id):
    return [
        Event('1', 'private', 'private', 'member', False, (bot_id,), 'hello'),
        Event('2', 'group', 'group', 'member', False, (), '@Bot JAT Design'),
        Event('3', 'group', 'group', 'member', False, (bot_id,), 'hello'),
        Event('3', 'group', 'group', 'member', False, (bot_id,), 'hello'),
    ]
