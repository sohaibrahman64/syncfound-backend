from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.chat_model import Conversation, ConversationMessage, ConversationParticipant, ConversationRead, MatchConversation


def normalize_user_pair(user_one_id: int, user_two_id: int) -> tuple[int, int]:
    return (min(user_one_id, user_two_id), max(user_one_id, user_two_id))


def get_or_create_direct_conversation(
    db: Session,
    user_one_id: int,
    user_two_id: int,
    created_by_user_id: int | None = None,
    created_from_invite_id: int | None = None,
) -> Conversation:
    user_a_id, user_b_id = normalize_user_pair(user_one_id, user_two_id)

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.kind == "direct",
            Conversation.user_a_id == user_a_id,
            Conversation.user_b_id == user_b_id,
        )
        .first()
    )
    if conversation is not None:
        if conversation.created_from_invite_id is None and created_from_invite_id is not None:
            conversation.created_from_invite_id = created_from_invite_id
        return conversation

    conversation = Conversation(
        kind="direct",
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        created_by_user_id=created_by_user_id,
        created_from_invite_id=created_from_invite_id,
    )
    db.add(conversation)
    db.flush()
    return conversation


def ensure_conversation_participants(db: Session, conversation_id: int, participant_user_ids: list[int]) -> None:
    if not participant_user_ids:
        return

    existing_rows = (
        db.query(ConversationParticipant.user_id)
        .filter(ConversationParticipant.conversation_id == conversation_id)
        .all()
    )
    existing_ids = {row.user_id for row in existing_rows}

    for user_id in participant_user_ids:
        if user_id in existing_ids:
            continue
        db.add(ConversationParticipant(conversation_id=conversation_id, user_id=user_id))


def link_match_to_conversation(db: Session, match_id: int, conversation_id: int) -> MatchConversation:
    existing = db.query(MatchConversation).filter(MatchConversation.match_id == match_id).first()
    if existing is not None:
        if existing.conversation_id != conversation_id:
            existing.conversation_id = conversation_id
        return existing

    row = MatchConversation(match_id=match_id, conversation_id=conversation_id)
    db.add(row)
    db.flush()
    return row


def create_conversation_message(
    db: Session,
    conversation_id: int,
    sender_user_id: int | None,
    message_text: str,
    message_kind: str = "text",
    source: str | None = None,
    source_invite_id: int | None = None,
    source_match_id: int | None = None,
    idempotency_key: str | None = None,
) -> ConversationMessage:
    normalized_text = message_text.strip()
    if not normalized_text:
        raise ValueError("message_text cannot be blank.")

    if idempotency_key:
        existing = (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing is not None:
            return existing

    message = ConversationMessage(
        conversation_id=conversation_id,
        sender_user_id=sender_user_id,
        message_kind=message_kind,
        message_text=normalized_text,
        source=source,
        source_invite_id=source_invite_id,
        source_match_id=source_match_id,
        idempotency_key=idempotency_key,
    )
    db.add(message)

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation is not None:
        now_utc = datetime.now(timezone.utc)
        conversation.last_message_at = now_utc
        conversation.updated_at = now_utc

    db.flush()
    return message


def upsert_conversation_read(
    db: Session,
    conversation_id: int,
    user_id: int,
    last_read_message_id: int,
    last_read_at: datetime,
) -> ConversationRead:
    row = (
        db.query(ConversationRead)
        .filter(
            ConversationRead.conversation_id == conversation_id,
            ConversationRead.user_id == user_id,
        )
        .first()
    )
    if row is None:
        row = ConversationRead(
            conversation_id=conversation_id,
            user_id=user_id,
            last_read_message_id=last_read_message_id,
            last_read_at=last_read_at,
        )
        db.add(row)
    else:
        row.last_read_message_id = last_read_message_id
        row.last_read_at = last_read_at

    db.flush()
    return row
