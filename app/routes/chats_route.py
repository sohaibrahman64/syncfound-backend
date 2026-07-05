from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat_model import Conversation, ConversationMessage, ConversationParticipant, ConversationRead, MatchConversation
from app.models.city_model import City
from app.models.country_new_model import CountryNew
from app.models.invite_model import Invite
from app.models.user_model import User
from app.models.user_profile_model import UserProfile
from app.schemas.chat_schema import (
    ChatConversationDetailsResponse,
    ChatConversationListItem,
    ChatConversationListResponse,
    ChatMessageItem,
    ChatMessageListResponse,
    ChatMessageSource,
    ChatUserSummary,
    MarkChatReadRequest,
    MarkChatReadResponse,
    SendChatMessageRequest,
    SendChatMessageResponse,
)
from app.services.chat_event_service import emit_chat_message_created_event, emit_chat_read_event
from app.services.chat_service import create_conversation_message, upsert_conversation_read
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["Chats"])


def _get_authenticated_user(authorization: str, db: Session) -> User:
    token_prefix = "Bearer "
    if not authorization or not authorization.startswith(token_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    firebase_token = authorization[len(token_prefix):].strip()
    if not firebase_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase token.",
        )

    try:
        decoded_token = verify_firebase_id_token(firebase_token)
    except (ValueError, firebase_exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token.",
        ) from exc

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain a valid uid.",
        )

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


def _build_list_cursor(event_at: datetime, row_id: int) -> str:
    payload = {"event_at": event_at.isoformat(), "id": row_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _parse_list_cursor(cursor: str | None) -> tuple[datetime, int] | None:
    if not cursor:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
        return datetime.fromisoformat(data["event_at"]), int(data["id"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor.") from exc


def _resolve_conversation_or_404(public_id: str, me_user_id: int, db: Session) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.public_id == public_id,
            ((Conversation.user_a_id == me_user_id) | (Conversation.user_b_id == me_user_id)),
        )
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


def _build_user_summary_map(user_ids: list[int], db: Session, joined_at_by_user: dict[int, datetime | None] | None = None) -> dict[int, ChatUserSummary]:
    if not user_ids:
        return {}

    joined_at_by_user = joined_at_by_user or {}

    rows = (
        db.query(
            User.id.label("user_id"),
            User.full_name.label("full_name"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            UserProfile.profile_image_uri.label("profile_photo_url"),
            UserProfile.title.label("title"),
            UserProfile.experience_location.label("location_text"),
            City.city_name.label("city"),
            CountryNew.iso2.label("country_code"),
        )
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(City, City.id == UserProfile.city_id)
        .outerjoin(CountryNew, CountryNew.id == City.country_id)
        .filter(User.id.in_(user_ids))
        .all()
    )

    result: dict[int, ChatUserSummary] = {}
    for row in rows:
        display_name = " ".join(part for part in [row.first_name, row.last_name] if part).strip() or row.full_name
        location_text = row.location_text
        if not location_text:
            location_parts = [part for part in [row.city, row.country_code] if part]
            location_text = ", ".join(location_parts) if location_parts else None

        result[row.user_id] = ChatUserSummary(
            user_id=row.user_id,
            full_name=row.full_name,
            display_name=display_name,
            profile_picture_url=row.profile_photo_url,
            profile_photo_url=row.profile_photo_url,
            title=row.title,
            location_text=location_text,
            joined_at=joined_at_by_user.get(row.user_id),
        )

    for user_id in user_ids:
        result.setdefault(user_id, ChatUserSummary(user_id=user_id, joined_at=joined_at_by_user.get(user_id)))

    return result


def _to_message_item(message: ConversationMessage, conversation_public_id: str, invite_public_id_map: dict[int, str]) -> ChatMessageItem:
    source = None
    if message.source or message.source_invite_id or message.source_match_id:
        source = ChatMessageSource(
            type=message.source,
            invite_id=invite_public_id_map.get(message.source_invite_id) if message.source_invite_id is not None else None,
            match_id=message.source_match_id,
        )

    return ChatMessageItem(
        message_id=str(message.public_id),
        conversation_id=str(conversation_public_id),
        message_kind=message.message_kind,
        message_text=message.message_text,
        sender_user_id=message.sender_user_id,
        created_at=message.created_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
        source=source,
    )


@router.get("/users/me/chats", response_model=ChatConversationListResponse)
def get_my_chats(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    cursor_tuple = _parse_list_cursor(cursor)

    query = db.query(Conversation).filter(
        (Conversation.user_a_id == user.id) | (Conversation.user_b_id == user.id)
    )

    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        query = query.filter(
            (
                (
                    (Conversation.last_message_at.isnot(None))
                    & (
                        (Conversation.last_message_at < cursor_dt)
                        | ((Conversation.last_message_at == cursor_dt) & (Conversation.id < cursor_id))
                    )
                )
                |
                (
                    (Conversation.last_message_at.is_(None))
                    & (
                        (Conversation.created_at < cursor_dt)
                        | ((Conversation.created_at == cursor_dt) & (Conversation.id < cursor_id))
                    )
                )
            )
        )

    rows = query.order_by(
        Conversation.last_message_at.desc().nullslast(),
        Conversation.created_at.desc(),
        Conversation.id.desc(),
    ).limit(limit + 1).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    conversation_ids = [row.id for row in rows]

    participant_ids = []
    for row in rows:
        participant_ids.extend([row.user_a_id, row.user_b_id])
    summary_map = _build_user_summary_map(list(set(participant_ids)), db)

    read_rows = (
        db.query(ConversationRead)
        .filter(ConversationRead.user_id == user.id, ConversationRead.conversation_id.in_(conversation_ids))
        .all()
    ) if conversation_ids else []
    read_by_conversation = {row.conversation_id: row for row in read_rows}

    message_rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id.in_(conversation_ids), ConversationMessage.deleted_at.is_(None))
        .order_by(ConversationMessage.conversation_id.asc(), ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .all()
    ) if conversation_ids else []

    invite_ids = list({row.source_invite_id for row in message_rows if row.source_invite_id is not None})
    invite_public_id_map = {}
    if invite_ids:
        invite_rows = db.query(Invite.id, Invite.public_id).filter(Invite.id.in_(invite_ids)).all()
        invite_public_id_map = {row.id: row.public_id for row in invite_rows}

    last_message_by_conversation: dict[int, ConversationMessage] = {}
    unread_count_by_conversation: dict[int, int] = {conversation_id: 0 for conversation_id in conversation_ids}

    for message in message_rows:
        if message.conversation_id not in last_message_by_conversation:
            last_message_by_conversation[message.conversation_id] = message

        if message.sender_user_id == user.id:
            continue

        read_marker = read_by_conversation.get(message.conversation_id)
        if read_marker is None or read_marker.last_read_at is None or message.created_at > read_marker.last_read_at:
            unread_count_by_conversation[message.conversation_id] += 1

    items = []
    for row in rows:
        other_user_id = row.user_b_id if row.user_a_id == user.id else row.user_a_id
        last_message = last_message_by_conversation.get(row.id)

        items.append(
            ChatConversationListItem(
                conversation_id=str(row.public_id),
                kind=row.kind,
                created_at=row.created_at,
                updated_at=row.updated_at,
                last_message_at=row.last_message_at,
                other_user=summary_map.get(other_user_id),
                last_message=_to_message_item(last_message, str(row.public_id), invite_public_id_map) if last_message is not None else None,
                unread_count=unread_count_by_conversation.get(row.id, 0),
            )
        )

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        cursor_dt = last.last_message_at or last.created_at
        next_cursor = _build_list_cursor(cursor_dt, last.id)

    return ChatConversationListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/users/me/chats/{conversation_id}", response_model=ChatConversationDetailsResponse)
def get_chat_details(
    conversation_id: str,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    conversation = _resolve_conversation_or_404(conversation_id, user.id, db)

    participant_rows = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id == conversation.id)
        .all()
    )

    joined_at_by_user = {row.user_id: row.joined_at for row in participant_rows}
    participant_ids = [row.user_id for row in participant_rows]

    if not participant_ids:
        participant_ids = [conversation.user_a_id, conversation.user_b_id]

    summary_map = _build_user_summary_map(participant_ids, db, joined_at_by_user)

    linked_match = db.query(MatchConversation).filter(MatchConversation.conversation_id == conversation.id).first()

    linked_invite_public_id = None
    if conversation.created_from_invite_id is not None:
        invite_row = db.query(Invite.public_id).filter(Invite.id == conversation.created_from_invite_id).first()
        linked_invite_public_id = invite_row.public_id if invite_row is not None else None

    return ChatConversationDetailsResponse(
        conversation_id=str(conversation.public_id),
        kind=conversation.kind,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        participants=[summary_map[user_id] for user_id in participant_ids if user_id in summary_map],
        linked_invite_id=linked_invite_public_id,
        linked_match_id=linked_match.match_id if linked_match is not None else None,
    )


@router.get("/users/me/chats/{conversation_id}/messages", response_model=ChatMessageListResponse)
def get_chat_messages(
    conversation_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    conversation = _resolve_conversation_or_404(conversation_id, user.id, db)

    query = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation.id,
        ConversationMessage.deleted_at.is_(None),
    )

    cursor_tuple = _parse_list_cursor(cursor)
    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        query = query.filter(
            (ConversationMessage.created_at < cursor_dt)
            | ((ConversationMessage.created_at == cursor_dt) & (ConversationMessage.id < cursor_id))
        )

    rows = query.order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    page_rows_desc = rows[:limit]

    invite_ids = [row.source_invite_id for row in page_rows_desc if row.source_invite_id is not None]
    invite_public_id_map = {}
    if invite_ids:
        invite_rows = db.query(Invite.id, Invite.public_id).filter(Invite.id.in_(invite_ids)).all()
        invite_public_id_map = {row.id: row.public_id for row in invite_rows}

    # Return messages oldest -> newest for easier chat rendering on the client.
    page_rows_asc = list(reversed(page_rows_desc))
    items = [_to_message_item(row, str(conversation.public_id), invite_public_id_map) for row in page_rows_asc]

    next_cursor = None
    if has_more and page_rows_desc:
        last = page_rows_desc[-1]
        next_cursor = _build_list_cursor(last.created_at, last.id)

    return ChatMessageListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post("/users/me/chats/{conversation_id}/messages", response_model=SendChatMessageResponse, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    conversation_id: str,
    payload: SendChatMessageRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    conversation = _resolve_conversation_or_404(conversation_id, user.id, db)

    message = create_conversation_message(
        db=db,
        conversation_id=conversation.id,
        sender_user_id=user.id,
        message_kind="text",
        message_text=payload.message_text,
        idempotency_key=payload.idempotency_key,
    )

    db.commit()
    db.refresh(message)

    recipient_user_id = conversation.user_b_id if conversation.user_a_id == user.id else conversation.user_a_id
    emit_chat_message_created_event(
        db=db,
        conversation=conversation,
        message=message,
        sender_user_id=user.id,
        recipient_user_id=recipient_user_id,
    )

    item = _to_message_item(message, str(conversation.public_id), {})
    return SendChatMessageResponse(message=item)


@router.patch("/users/me/chats/{conversation_id}/read", response_model=MarkChatReadResponse)
def mark_chat_read(
    conversation_id: str,
    payload: MarkChatReadRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    conversation = _resolve_conversation_or_404(conversation_id, user.id, db)
    message = None
    try:
        last_read_message_uuid = UUID(payload.last_read_message_id)
        message = (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.public_id == last_read_message_uuid,
                ConversationMessage.conversation_id == conversation.id,
            )
            .first()
        )
    except ValueError:
        # Some clients may send optimistic local IDs before server UUIDs are reconciled.
        message = (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.idempotency_key == payload.last_read_message_id,
                ConversationMessage.conversation_id == conversation.id,
            )
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .first()
        )

    if message is None:
        # Fallback: mark read up to the latest persisted message in this conversation.
        message = (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.deleted_at.is_(None),
            )
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .first()
        )

    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    now_utc = datetime.now(timezone.utc)
    read_row = upsert_conversation_read(
        db=db,
        conversation_id=conversation.id,
        user_id=user.id,
        last_read_message_id=message.id,
        last_read_at=now_utc,
    )

    unread_count = (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.conversation_id == conversation.id,
            ConversationMessage.deleted_at.is_(None),
            ConversationMessage.sender_user_id != user.id,
            ConversationMessage.created_at > message.created_at,
        )
        .count()
    )

    db.commit()

    recipient_user_id = conversation.user_b_id if conversation.user_a_id == user.id else conversation.user_a_id
    emit_chat_read_event(
        db=db,
        conversation=conversation,
        reader_user_id=user.id,
        recipient_user_id=recipient_user_id,
        last_read_message_id=str(message.public_id),
    )

    return MarkChatReadResponse(
        conversation_id=str(conversation.public_id),
        last_read_message_id=str(message.public_id),
        last_read_at=read_row.last_read_at,
        unread_count=unread_count,
    )
