"""Internal events ONLY: these field names are not a Zalo API schema."""
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple

REPLY = 'JAT Design đã nhận được lời nhắc của bạn.'


@dataclass(frozen=True)
class Event:
    event_id: str
    chat_id: str
    chat_kind: str
    sender_id: str
    sender_is_bot: bool
    mentioned_ids: Tuple[str, ...]
    text: str


class BotAPI(Protocol):
    """Internal interface, not the HTTP signature of the official methods."""

    def getUpdates(self) -> Optional[Event]:
        ...

    def sendMessage(self, chat_id: str, text: str) -> None:
        ...


class DeliveryUncertain(Exception):
    """Do not retry a send whose server-side outcome is unknown."""


class Engine:
    def __init__(self, bot_id: str, store):
        if not isinstance(bot_id, str) or not bot_id.strip():
            raise ValueError('Bot ID is required')
        self.bot_id = bot_id
        self.store = store

    def eligible(self, event: Event) -> bool:
        return (
            isinstance(event, Event)
            and all(isinstance(v, str) and bool(v.strip()) for v in
                    (event.event_id, event.chat_id, event.sender_id))
            and event.chat_kind == 'group'
            and event.sender_is_bot is False
            and event.sender_id != self.bot_id
            and isinstance(event.text, str)
            and bool(event.text.strip())
            and isinstance(event.mentioned_ids, tuple)
            and self.bot_id in event.mentioned_ids
        )

    def step(self, api: BotAPI) -> str:
        event = api.getUpdates()
        if event is None:
            return 'idle'
        if not self.eligible(event):
            return 'ignored'
        # Reserve before send; a crash or timeout must not cause duplicate replies.
        # This is at-most-once processing, with possible loss requiring review.
        if not self.store.reserve(event.chat_id, event.event_id):
            return 'duplicate'
        try:
            api.sendMessage(event.chat_id, REPLY)
        except Exception:
            self.store.mark(event.chat_id, event.event_id, 'uncertain')
            raise DeliveryUncertain('Send outcome uncertain; automatic retry disabled') from None
        self.store.mark(event.chat_id, event.event_id, 'sent')
        return 'sent'
