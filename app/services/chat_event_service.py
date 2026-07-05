from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat_model import Conversation, ConversationMessage
from app.models.user_device_token_model import UserDeviceToken
from app.models.user_model import User
from app.services.firebase_service import send_fcm_multicast


logger = logging.getLogger(__name__)


def _active_fcm_tokens_for_user(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(UserDeviceToken.token)
        .filter(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.provider == "fcm",
            UserDeviceToken.is_active.is_(True),
        )
        .all()
    )
    return [row.token for row in rows]


def _sender_name(db: Session, sender_user_id: int) -> str:
    row = db.query(User.full_name).filter(User.id == sender_user_id).first()
    if row is None or not row.full_name:
        return "New message"
    return row.full_name


def emit_chat_message_created_event(
    db: Session,
    conversation: Conversation,
    message: ConversationMessage,
    sender_user_id: int,
    recipient_user_id: int,
) -> None:
    tokens = _active_fcm_tokens_for_user(db, recipient_user_id)
    if not tokens:
        return

    preview = (message.message_text or "").strip()
    if len(preview) > 120:
        preview = preview[:117] + "..."

    payload = {
        "type": "chat.message.created",
        "conversation_id": str(conversation.public_id),
        "message_id": str(message.public_id),
        "sender_user_id": str(sender_user_id),
        "recipient_user_id": str(recipient_user_id),
        "message_kind": message.message_kind,
        "preview_text": preview,
        "created_at": message.created_at.isoformat() if message.created_at else datetime.now(timezone.utc).isoformat(),
    }

    try:
        send_fcm_multicast(
            tokens=tokens,
            data={k: str(v) for k, v in payload.items()},
            title=_sender_name(db, sender_user_id),
            body=preview or "Sent you a message",
        )
    except Exception:
        logger.exception("Failed to emit chat.message.created event", extra={"recipient_user_id": recipient_user_id})


def emit_chat_read_event(
    db: Session,
    conversation: Conversation,
    reader_user_id: int,
    recipient_user_id: int,
    last_read_message_id: str,
) -> None:
    tokens = _active_fcm_tokens_for_user(db, recipient_user_id)
    if not tokens:
        return

    payload = {
        "type": "chat.message.read",
        "conversation_id": str(conversation.public_id),
        "reader_user_id": str(reader_user_id),
        "recipient_user_id": str(recipient_user_id),
        "last_read_message_id": str(last_read_message_id),
        "read_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        send_fcm_multicast(
            tokens=tokens,
            data={k: str(v) for k, v in payload.items()},
            title=None,
            body=None,
        )
    except Exception:
        logger.exception("Failed to emit chat.message.read event", extra={"recipient_user_id": recipient_user_id})
