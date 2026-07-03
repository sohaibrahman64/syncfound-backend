from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_conversations_public_id"),
        UniqueConstraint("kind", "user_a_id", "user_b_id", name="uq_conversations_direct_pair"),
        CheckConstraint("kind IN ('direct')", name="chk_conversations_kind"),
        CheckConstraint("user_a_id < user_b_id", name="chk_conversations_user_order"),
        Index("idx_conversations_updated", "updated_at", "id"),
        Index("idx_conversations_last_message", "last_message_at", "id"),
        Index("idx_conversations_created_from_invite", "created_from_invite_id"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String(36), nullable=False, default=lambda: str(uuid4()))
    kind = Column(String(20), nullable=False, default="direct")

    user_a_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_b_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_from_invite_id = Column(BigInteger, ForeignKey("invites.id", ondelete="SET NULL"), nullable=True)

    last_message_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at = Column(TIMESTAMP(timezone=True), nullable=True)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        PrimaryKeyConstraint("conversation_id", "user_id", name="pk_conversation_participants"),
        Index("idx_conversation_participants_user", "user_id", "conversation_id"),
    )

    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    joined_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    left_at = Column(TIMESTAMP(timezone=True), nullable=True)
    muted_until = Column(TIMESTAMP(timezone=True), nullable=True)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_conversation_messages_public_id"),
        UniqueConstraint("conversation_id", "idempotency_key", name="uq_conversation_messages_idempotency"),
        CheckConstraint("message_kind IN ('text', 'acceptance_note', 'system')", name="chk_conversation_messages_kind"),
        CheckConstraint(
            "((message_kind = 'system' AND sender_user_id IS NULL) OR (message_kind <> 'system' AND sender_user_id IS NOT NULL))",
            name="chk_conversation_messages_sender",
        ),
        CheckConstraint("length(trim(message_text)) > 0", name="chk_conversation_messages_not_blank"),
        CheckConstraint("length(message_text) <= 4000", name="chk_conversation_messages_len"),
        Index("idx_conversation_messages_timeline", "conversation_id", "created_at", "id"),
        Index("idx_conversation_messages_sender_time", "sender_user_id", "created_at"),
        Index(
            "uq_conversation_messages_acceptance_once_per_invite",
            "source_invite_id",
            unique=True,
            postgresql_where=text("source_invite_id IS NOT NULL AND message_kind = 'acceptance_note'"),
        ),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String(36), nullable=False, default=lambda: str(uuid4()))

    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    message_kind = Column(String(30), nullable=False, default="text")
    message_text = Column(Text, nullable=False)

    source = Column(String(40), nullable=True)
    source_invite_id = Column(BigInteger, ForeignKey("invites.id", ondelete="SET NULL"), nullable=True, index=True)
    source_match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True, index=True)

    idempotency_key = Column(String(150), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    edited_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)


class ConversationRead(Base):
    __tablename__ = "conversation_reads"
    __table_args__ = (
        PrimaryKeyConstraint("conversation_id", "user_id", name="pk_conversation_reads"),
        Index("idx_conversation_reads_user", "user_id", "last_read_at"),
    )

    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    last_read_message_id = Column(BigInteger, ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    last_read_at = Column(TIMESTAMP(timezone=True), nullable=True)


class MatchConversation(Base):
    __tablename__ = "match_conversations"

    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    linked_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
