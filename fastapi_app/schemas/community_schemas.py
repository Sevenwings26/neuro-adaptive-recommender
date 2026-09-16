# schemas/community_schemas.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ── Circles ──────────────────────────────────────────────────────────────────
class CircleResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    icon: str
    order_num: int
    post_count: int = 0

    class Config:
        from_attributes = True


# ── Posts ────────────────────────────────────────────────────────────────────
class PostCreate(BaseModel):
    circle_id: UUID
    title: str = Field(..., min_length=3, max_length=255)
    body: str = Field(..., min_length=10)
    post_type: str = Field("question", description="question, experience, concern, resource_tip")
    is_anonymous: bool = False
    child_id: Optional[UUID] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None


class PostSummaryResponse(BaseModel):
    id: UUID
    circle_id: UUID
    circle_name: str
    circle_icon: str
    author_id: int
    author_name: str
    is_anonymous: bool
    author_flair: Optional[str] = None
    title: str
    body: str
    post_type: str
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    views_count: int
    is_pinned: bool
    replies_count: int = 0
    reactions_count: Dict[str, int] = Field(default_factory=lambda: {"support": 0, "relate": 0, "helpful": 0, "celebrate": 0})
    user_reactions: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


# ── Replies ──────────────────────────────────────────────────────────────────
class ReplyCreate(BaseModel):
    body: str = Field(..., min_length=2)
    is_anonymous: bool = False
    child_id: Optional[UUID] = None


class ReplyResponse(BaseModel):
    id: UUID
    post_id: UUID
    author_id: int
    author_name: str
    is_anonymous: bool
    author_flair: Optional[str] = None
    is_clinician: bool = False
    is_clinician_endorsed: bool = False
    endorsed_by_clinician_name: Optional[str] = None
    body: str
    reactions_count: Dict[str, int] = Field(default_factory=lambda: {"support": 0, "relate": 0, "helpful": 0, "celebrate": 0})
    user_reactions: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class PostDetailResponse(PostSummaryResponse):
    replies: List[ReplyResponse] = Field(default_factory=list)
    evidence_spotlight: List[Dict[str, Any]] = Field(default_factory=list)


# ── Reactions ────────────────────────────────────────────────────────────────
class ReactionToggle(BaseModel):
    reaction_type: str = Field(..., description="support, relate, helpful, celebrate")


# ── Local Resources ──────────────────────────────────────────────────────────
class LocalResourceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    category: str = Field(..., description="clinic, sensory_venue, support_group, education, financial_grant")
    description: str = Field(..., min_length=10)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=50)
    address_or_url: Optional[str] = None
    contact_info: Optional[str] = None


class LocalResourceResponse(BaseModel):
    id: UUID
    name: str
    category: str
    description: str
    city: str
    state: str
    address_or_url: Optional[str] = None
    contact_info: Optional[str] = None
    upvotes_count: int = 0
    is_verified: bool = False
    submitted_by_name: str
    user_has_upvoted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
