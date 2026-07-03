from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatUserSummary(BaseModel):
    user_id: int
    full_name: str | None = None
    display_name: str | None = None
    profile_picture_url: str | None = None
    profile_photo_url: str | None = None
    title: str | None = None
    location_text: str | None = None
    joined_at: datetime | None = None


class ChatMessageSource(BaseModel):
    type: str | None = None
    invite_id: str | None = None
    match_id: int | None = None


class ChatMessageItem(BaseModel):
    message_id: str
    conversation_id: str
    message_kind: str
    message_text: str
    sender_user_id: int | None = None
    created_at: datetime
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    source: ChatMessageSource | None = None


class ChatConversationListItem(BaseModel):
    conversation_id: str
    kind: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    other_user: ChatUserSummary | None = None
    last_message: ChatMessageItem | None = None
    unread_count: int = 0


class ChatConversationListResponse(BaseModel):
    items: list[ChatConversationListItem]
    next_cursor: str | None = None
    has_more: bool


class ChatConversationDetailsResponse(BaseModel):
    conversation_id: str
    kind: str
    created_at: datetime
    updated_at: datetime
    participants: list[ChatUserSummary] = Field(default_factory=list)
    linked_invite_id: str | None = None
    linked_match_id: int | None = None


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageItem]
    next_cursor: str | None = None
    has_more: bool


class SendChatMessageRequest(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, max_length=150)


class SendChatMessageResponse(BaseModel):
    message: ChatMessageItem


class MarkChatReadRequest(BaseModel):
    last_read_message_id: str


class MarkChatReadResponse(BaseModel):
    conversation_id: str
    last_read_message_id: str
    last_read_at: datetime
    unread_count: int
