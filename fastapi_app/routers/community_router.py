# routers/community_router.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from models.auth_models import User
from schemas.community_schemas import (
    CircleResponse,
    PostCreate,
    PostSummaryResponse,
    PostDetailResponse,
    ReplyCreate,
    ReplyResponse,
    ReactionToggle,
    LocalResourceCreate,
    LocalResourceResponse,
)
from services.auth_service import get_current_user, RoleChecker
from services.community_service import CommunityService
from services.local_resource_service import LocalResourceService

community_router = APIRouter(prefix="/api/v1/community", tags=["Caregiver Village & Community"])


async def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Helper to retrieve user from Bearer header or cookie if present, without raising 401."""
    try:
        from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
        auth_header = request.headers.get("Authorization")
        creds = None
        if auth_header and auth_header.startswith("Bearer "):
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_header[7:])
        return await get_current_user(request, creds, db)
    except Exception:
        return None


# ── Circles ──────────────────────────────────────────────────────────────────
@community_router.get("/circles", response_model=List[CircleResponse])
def list_circles(db: Session = Depends(get_db)):
    """Retrieve all topical caregiver circles with active discussion counts."""
    return CommunityService.get_circles(db)


# ── Posts ────────────────────────────────────────────────────────────────────
@community_router.get("/posts", response_model=List[PostSummaryResponse])
async def list_posts(
    circle_id: Optional[UUID] = Query(None, description="Filter by Circle UUID"),
    circle_slug: Optional[str] = Query(None, description="Filter by Circle slug (e.g. 'speech-aac')"),
    post_type: Optional[str] = Query(None, description="Filter by post type: question, experience, concern, resource_tip"),
    q: Optional[str] = Query(None, description="Search keyword in title or body"),
    sort: str = Query("newest", description="'newest' or 'popular'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Retrieve discussion feed filtered by circle, topic, or search query."""
    current_user = await get_optional_user(request, db)
    return CommunityService.list_posts(
        db=db,
        current_user=current_user,
        circle_id=circle_id,
        circle_slug=circle_slug,
        post_type=post_type,
        search_query=q,
        sort_by=sort,
        limit=limit,
        offset=offset
    )


@community_router.post("/posts", response_model=PostSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish a new caregiver question, breakthrough experience, or developmental concern."""
    return CommunityService.create_post(db=db, user=current_user, data=data)


@community_router.get("/posts/{post_id}", response_model=PostDetailResponse)
async def get_post_detail(
    post_id: UUID,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Fetch post details, threaded caregiver replies, reactions, and RAG Clinical Evidence Spotlight."""
    current_user = await get_optional_user(request, db)
    return CommunityService.get_post_detail(db=db, post_id=post_id, current_user=current_user)


@community_router.post("/posts/{post_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
def add_reply(
    post_id: UUID,
    data: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post a supportive answer, shared experience, or tip in response to a caregiver discussion."""
    return CommunityService.add_reply(db=db, user=current_user, post_id=post_id, data=data)


# ── Reactions ────────────────────────────────────────────────────────────────
@community_router.post("/posts/{post_id}/react")
def react_to_post(
    post_id: UUID,
    data: ReactionToggle,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle a neuro-affirming empathy reaction (support, relate, helpful, celebrate) on a post."""
    return CommunityService.toggle_reaction(
        db=db,
        user=current_user,
        target_type="post",
        target_id=post_id,
        reaction_type=data.reaction_type
    )


@community_router.post("/replies/{reply_id}/react")
def react_to_reply(
    reply_id: UUID,
    data: ReactionToggle,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle a neuro-affirming empathy reaction on a reply."""
    return CommunityService.toggle_reaction(
        db=db,
        user=current_user,
        target_type="reply",
        target_id=reply_id,
        reaction_type=data.reaction_type
    )


# ── Clinician Endorsement ───────────────────────────────────────────────────
@community_router.post("/replies/{reply_id}/endorse", response_model=ReplyResponse)
def endorse_reply(
    reply_id: UUID,
    current_user: User = Depends(RoleChecker(["clinician"])),
    db: Session = Depends(get_db)
):
    """Clinician-only: Endorse or validate parent-to-parent advice as clinically sound."""
    return CommunityService.endorse_reply(db=db, clinician_user=current_user, reply_id=reply_id)


# ── Local Resources Directory ────────────────────────────────────────────────
@community_router.get("/resources", response_model=List[LocalResourceResponse])
async def list_local_resources(
    category: Optional[str] = Query(None, description="clinic, sensory_venue, support_group, education, financial_grant"),
    city: Optional[str] = Query(None, description="City name filter"),
    state: Optional[str] = Query(None, description="State abbreviation filter"),
    q: Optional[str] = Query(None, description="Search term"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Browse parent-reviewed local opportunities, clinics, sensory gyms, and adaptive events."""
    current_user = await get_optional_user(request, db)
    return LocalResourceService.list_resources(
        db=db,
        current_user=current_user,
        category=category,
        city=city,
        state=state,
        search_query=q,
        limit=limit,
        offset=offset
    )


@community_router.post("/resources", response_model=LocalResourceResponse, status_code=status.HTTP_201_CREATED)
def create_local_resource(
    data: LocalResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a local sensory-friendly venue, pediatric therapy clinic, or caregiver support circle."""
    return LocalResourceService.create_resource(db=db, user=current_user, data=data)


@community_router.post("/resources/{resource_id}/upvote")
def upvote_local_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle upvote / helpful vote on a local resource."""
    return LocalResourceService.toggle_resource_upvote(db=db, user=current_user, resource_id=resource_id)
