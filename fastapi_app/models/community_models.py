# models/community_models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, Uuid, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


class CommunityCircle(Base):
    __tablename__ = "community_circles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(20), nullable=False)  # emoji or icon token
    order_num = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    posts = relationship(
        "CommunityPost",
        back_populates="circle",
        cascade="all, delete-orphan",
        order_by="CommunityPost.created_at.desc()"
    )


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    circle_id = Column(Uuid(as_uuid=True), ForeignKey("community_circles.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    post_type = Column(String(50), default="question", nullable=False)  # question, experience, concern, resource_tip
    is_anonymous = Column(Boolean, default=False, nullable=False)
    author_flair = Column(String(100), nullable=True)  # e.g. "Parent of 2yo • Sensory Focus"
    location_city = Column(String(100), nullable=True)
    location_state = Column(String(100), nullable=True)
    views_count = Column(Integer, default=0, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    circle = relationship("CommunityCircle", back_populates="posts")
    author = relationship("User", back_populates="community_posts")
    replies = relationship(
        "CommunityReply",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="CommunityReply.created_at.asc()"
    )
    reactions = relationship(
        "CommunityReaction",
        back_populates="post",
        cascade="all, delete-orphan"
    )


class CommunityReply(Base):
    __tablename__ = "community_replies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    post_id = Column(Uuid(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    author_flair = Column(String(100), nullable=True)
    is_clinician_endorsed = Column(Boolean, default=False, nullable=False)
    endorsed_by_clinician_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    post = relationship("CommunityPost", back_populates="replies")
    author = relationship("User", foreign_keys=[author_id], back_populates="community_replies")
    endorsed_by_clinician = relationship("User", foreign_keys=[endorsed_by_clinician_id])
    reactions = relationship(
        "CommunityReaction",
        back_populates="reply",
        cascade="all, delete-orphan"
    )


class CommunityReaction(Base):
    __tablename__ = "community_reactions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(Uuid(as_uuid=True), ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    reply_id = Column(Uuid(as_uuid=True), ForeignKey("community_replies.id", ondelete="CASCADE"), nullable=True, index=True)
    reaction_type = Column(String(30), nullable=False)  # support, relate, helpful, celebrate
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", "reaction_type", name="uq_user_post_reaction"),
        UniqueConstraint("user_id", "reply_id", "reaction_type", name="uq_user_reply_reaction"),
    )

    # Relationships
    user = relationship("User")
    post = relationship("CommunityPost", back_populates="reactions")
    reply = relationship("CommunityReply", back_populates="reactions")


class LocalResource(Base):
    __tablename__ = "local_resources"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    submitted_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # clinic, sensory_venue, support_group, education, financial_grant
    description = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    address_or_url = Column(String(255), nullable=True)
    contact_info = Column(String(100), nullable=True)
    upvotes_count = Column(Integer, default=0, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    submitted_by = relationship("User", back_populates="submitted_resources")
    votes = relationship("LocalResourceVote", back_populates="resource", cascade="all, delete-orphan")


class LocalResourceVote(Base):
    __tablename__ = "local_resource_votes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Uuid(as_uuid=True), ForeignKey("local_resources.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="uq_user_resource_vote"),
    )

    # Relationships
    user = relationship("User")
    resource = relationship("LocalResource", back_populates="votes")
