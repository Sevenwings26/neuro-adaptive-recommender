# services/community_service.py
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException, status

from models.auth_models import User
from models.domain_models import ChildProfile
from models.community_models import (
    CommunityCircle,
    CommunityPost,
    CommunityReply,
    CommunityReaction,
)
from schemas.community_schemas import (
    PostCreate,
    ReplyCreate,
    PostSummaryResponse,
    PostDetailResponse,
    ReplyResponse,
    CircleResponse,
)
from services.rag_evidence_service import EvidenceRAGService

log = logging.getLogger(__name__)

DEFAULT_CIRCLES = [
    {
        "slug": "speech-aac",
        "name": "Speech & Nonverbal / AAC",
        "description": "First words, gestures, AAC speech devices (Proloquo2Go, LAMP), and communication breakthroughs.",
        "icon": "🗣️",
        "order_num": 1,
    },
    {
        "slug": "sensory-meltdowns",
        "name": "Sensory Processing & Meltdowns",
        "description": "Managing sensory overload, sound/texture aversions, calming routines, and gentle de-escalation.",
        "icon": "⚡",
        "order_num": 2,
    },
    {
        "slug": "toddlers-12-24m",
        "name": "Early Toddlers (12–24m)",
        "description": "Navigating first milestones, joint attention, name response, and early intervention pathways.",
        "icon": "🧩",
        "order_num": 3,
    },
    {
        "slug": "preschool-24-48m",
        "name": "Preschool & Transitions (24–48m)",
        "description": "Pre-K readiness, social play, potty routines, and transitioning between activities.",
        "icon": "🎒",
        "order_num": 4,
    },
    {
        "slug": "routines-sleep-eating",
        "name": "Routines, Sleep & Picky Eating",
        "description": "Visual schedules, bedtime struggles, sensory food aversions, and daily consistency.",
        "icon": "🍽️",
        "order_num": 5,
    },
    {
        "slug": "clinical-evals",
        "name": "Clinical Evaluations & Diagnosis",
        "description": "Waitlists, developmental pediatricians, speech/OT evaluations, and insurance navigation.",
        "icon": "🩺",
        "order_num": 6,
    },
    {
        "slug": "local-opportunities",
        "name": "Local Opportunities & Meetups",
        "description": "Discovering local sensory-friendly venues, adaptive parks, and caregiver support groups.",
        "icon": "📍",
        "order_num": 7,
    },
]


class CommunityService:

    @staticmethod
    def seed_default_circles(db: Session):
        """Seed default community circles if not yet present."""
        for c_data in DEFAULT_CIRCLES:
            existing = db.query(CommunityCircle).filter(CommunityCircle.slug == c_data["slug"]).first()
            if not existing:
                circle = CommunityCircle(
                    slug=c_data["slug"],
                    name=c_data["name"],
                    description=c_data["description"],
                    icon=c_data["icon"],
                    order_num=c_data["order_num"],
                )
                db.add(circle)
        db.commit()
        log.info("✓ Seeded default Community Circles")

    @staticmethod
    def get_circles(db: Session) -> List[CircleResponse]:
        """Fetch all circles with active post counts."""
        circles = db.query(CommunityCircle).order_by(CommunityCircle.order_num.asc()).all()
        result = []
        for c in circles:
            cnt = db.query(func.count(CommunityPost.id)).filter(CommunityPost.circle_id == c.id).scalar() or 0
            result.append(CircleResponse(
                id=c.id,
                slug=c.slug,
                name=c.name,
                description=c.description,
                icon=c.icon,
                order_num=c.order_num,
                post_count=cnt
            ))
        return result

    @staticmethod
    def generate_author_flair(db: Session, user: User, child_id: Optional[UUID] = None) -> str:
        """Construct supportive, privacy-safe developmental persona flair."""
        if getattr(user, "role", "") == "clinician":
            return "Verified Pediatric Clinician"

        child = None
        if child_id:
            child = db.query(ChildProfile).filter(ChildProfile.id == child_id, ChildProfile.user_id == user.id).first()
        if not child:
            child = db.query(ChildProfile).filter(ChildProfile.user_id == user.id).first()

        if child and child.date_of_birth:
            days = (datetime.now(timezone.utc).date() - child.date_of_birth).days
            months = max(1, int(round(days / 30.4375)))
            if months < 24:
                age_tag = f"Parent of {months}mo"
            else:
                years = max(1, round(months / 12))
                age_tag = f"Parent of {years}yo"

            # Check if child has logged meltdowns or assessments
            if child.meltdowns and len(child.meltdowns) > 0:
                return f"{age_tag} • Sensory Profile"
            return f"{age_tag} • Toddler Journey"

        return "Caregiver Member"

    @staticmethod
    def _get_reactions_data(db: Session, target_type: str, target_id: UUID, current_user_id: Optional[int]) -> Tuple[Dict[str, int], List[str]]:
        """Compute reaction counts and current user's reaction list."""
        if target_type == "post":
            reactions = db.query(CommunityReaction).filter(CommunityReaction.post_id == target_id).all()
        else:
            reactions = db.query(CommunityReaction).filter(CommunityReaction.reply_id == target_id).all()

        counts = {"support": 0, "relate": 0, "helpful": 0, "celebrate": 0}
        user_reacts = []
        for r in reactions:
            if r.reaction_type in counts:
                counts[r.reaction_type] += 1
            if current_user_id and r.user_id == current_user_id:
                user_reacts.append(r.reaction_type)
        return counts, user_reacts

    @classmethod
    def list_posts(
        cls,
        db: Session,
        current_user: Optional[User] = None,
        circle_id: Optional[UUID] = None,
        circle_slug: Optional[str] = None,
        post_type: Optional[str] = None,
        search_query: Optional[str] = None,
        sort_by: str = "newest",
        limit: int = 50,
        offset: int = 0
    ) -> List[PostSummaryResponse]:
        query = db.query(CommunityPost).join(CommunityCircle)

        if circle_id:
            query = query.filter(CommunityPost.circle_id == circle_id)
        elif circle_slug:
            query = query.filter(CommunityCircle.slug == circle_slug)

        if post_type and post_type != "all":
            query = query.filter(CommunityPost.post_type == post_type)

        if search_query:
            pattern = f"%{search_query}%"
            query = query.filter(or_(CommunityPost.title.ilike(pattern), CommunityPost.body.ilike(pattern)))

        if sort_by == "popular":
            query = query.order_by(CommunityPost.views_count.desc(), CommunityPost.created_at.desc())
        else:
            query = query.order_by(CommunityPost.is_pinned.desc(), CommunityPost.created_at.desc())

        posts = query.offset(offset).limit(limit).all()
        results = []
        current_user_id = current_user.id if current_user else None

        for p in posts:
            counts, user_reacts = cls._get_reactions_data(db, "post", p.id, current_user_id)
            replies_cnt = db.query(func.count(CommunityReply.id)).filter(CommunityReply.post_id == p.id).scalar() or 0

            author_name = "Anonymous Caregiver" if p.is_anonymous else p.author.username

            results.append(PostSummaryResponse(
                id=p.id,
                circle_id=p.circle_id,
                circle_name=p.circle.name,
                circle_icon=p.circle.icon,
                author_id=p.author_id,
                author_name=author_name,
                is_anonymous=p.is_anonymous,
                author_flair=p.author_flair,
                title=p.title,
                body=p.body,
                post_type=p.post_type,
                location_city=p.location_city,
                location_state=p.location_state,
                views_count=p.views_count,
                is_pinned=p.is_pinned,
                replies_count=replies_cnt,
                reactions_count=counts,
                user_reactions=user_reacts,
                created_at=p.created_at
            ))
        return results

    @classmethod
    def create_post(cls, db: Session, user: User, data: PostCreate) -> PostSummaryResponse:
        circle = db.query(CommunityCircle).filter(CommunityCircle.id == data.circle_id).first()
        if not circle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community Circle not found")

        flair = cls.generate_author_flair(db, user, data.child_id)

        post = CommunityPost(
            circle_id=data.circle_id,
            author_id=user.id,
            title=data.title,
            body=data.body,
            post_type=data.post_type,
            is_anonymous=data.is_anonymous,
            author_flair=flair,
            location_city=data.location_city,
            location_state=data.location_state,
            views_count=0,
            is_pinned=False
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        author_name = "Anonymous Caregiver" if post.is_anonymous else user.username
        return PostSummaryResponse(
            id=post.id,
            circle_id=post.circle_id,
            circle_name=circle.name,
            circle_icon=circle.icon,
            author_id=post.author_id,
            author_name=author_name,
            is_anonymous=post.is_anonymous,
            author_flair=post.author_flair,
            title=post.title,
            body=post.body,
            post_type=post.post_type,
            location_city=post.location_city,
            location_state=post.location_state,
            views_count=post.views_count,
            is_pinned=post.is_pinned,
            replies_count=0,
            reactions_count={"support": 0, "relate": 0, "helpful": 0, "celebrate": 0},
            user_reactions=[],
            created_at=post.created_at
        )

    @classmethod
    def get_post_detail(cls, db: Session, post_id: UUID, current_user: Optional[User] = None) -> PostDetailResponse:
        post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion post not found")

        # Increment view count
        post.views_count += 1
        db.commit()

        current_user_id = current_user.id if current_user else None
        p_counts, p_user_reacts = cls._get_reactions_data(db, "post", post.id, current_user_id)

        # Fetch replies
        replies_data = []
        for rep in post.replies:
            r_counts, r_user_reacts = cls._get_reactions_data(db, "reply", rep.id, current_user_id)
            r_author_name = "Anonymous Caregiver" if rep.is_anonymous else rep.author.username
            is_clinician = getattr(rep.author, "role", "") == "clinician"

            endorser_name = rep.endorsed_by_clinician.username if rep.endorsed_by_clinician else None

            replies_data.append(ReplyResponse(
                id=rep.id,
                post_id=rep.post_id,
                author_id=rep.author_id,
                author_name=r_author_name,
                is_anonymous=rep.is_anonymous,
                author_flair=rep.author_flair,
                is_clinician=is_clinician,
                is_clinician_endorsed=rep.is_clinician_endorsed,
                endorsed_by_clinician_name=endorser_name,
                body=rep.body,
                reactions_count=r_counts,
                user_reactions=r_user_reacts,
                created_at=rep.created_at
            ))

        # Query RAG Clinical Evidence Spotlight based on post topic
        rag_query = f"{post.title} {post.body[:120]}"
        evidence_results = EvidenceRAGService.search_evidence(query=rag_query, top_k=2)

        author_name = "Anonymous Caregiver" if post.is_anonymous else post.author.username
        return PostDetailResponse(
            id=post.id,
            circle_id=post.circle_id,
            circle_name=post.circle.name,
            circle_icon=post.circle.icon,
            author_id=post.author_id,
            author_name=author_name,
            is_anonymous=post.is_anonymous,
            author_flair=post.author_flair,
            title=post.title,
            body=post.body,
            post_type=post.post_type,
            location_city=post.location_city,
            location_state=post.location_state,
            views_count=post.views_count,
            is_pinned=post.is_pinned,
            replies_count=len(replies_data),
            reactions_count=p_counts,
            user_reactions=p_user_reacts,
            created_at=post.created_at,
            replies=replies_data,
            evidence_spotlight=evidence_results
        )

    @classmethod
    def add_reply(cls, db: Session, user: User, post_id: UUID, data: ReplyCreate) -> ReplyResponse:
        post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion post not found")

        flair = cls.generate_author_flair(db, user, data.child_id)

        reply = CommunityReply(
            post_id=post_id,
            author_id=user.id,
            body=data.body,
            is_anonymous=data.is_anonymous,
            author_flair=flair,
            is_clinician_endorsed=False
        )
        db.add(reply)
        db.commit()
        db.refresh(reply)

        author_name = "Anonymous Caregiver" if reply.is_anonymous else user.username
        is_clinician = getattr(user, "role", "") == "clinician"

        return ReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            author_id=reply.author_id,
            author_name=author_name,
            is_anonymous=reply.is_anonymous,
            author_flair=reply.author_flair,
            is_clinician=is_clinician,
            is_clinician_endorsed=False,
            endorsed_by_clinician_name=None,
            body=reply.body,
            reactions_count={"support": 0, "relate": 0, "helpful": 0, "celebrate": 0},
            user_reactions=[],
            created_at=reply.created_at
        )

    @classmethod
    def toggle_reaction(
        cls,
        db: Session,
        user: User,
        target_type: str,
        target_id: UUID,
        reaction_type: str
    ) -> Dict[str, Any]:
        valid_reactions = {"support", "relate", "helpful", "celebrate"}
        if reaction_type not in valid_reactions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid reaction_type. Must be one of {valid_reactions}"
            )

        if target_type == "post":
            existing = db.query(CommunityReaction).filter(
                CommunityReaction.user_id == user.id,
                CommunityReaction.post_id == target_id,
                CommunityReaction.reaction_type == reaction_type
            ).first()
            if existing:
                db.delete(existing)
            else:
                db.add(CommunityReaction(
                    user_id=user.id,
                    post_id=target_id,
                    reaction_type=reaction_type
                ))
            db.commit()
            counts, user_reacts = cls._get_reactions_data(db, "post", target_id, user.id)
        elif target_type == "reply":
            existing = db.query(CommunityReaction).filter(
                CommunityReaction.user_id == user.id,
                CommunityReaction.reply_id == target_id,
                CommunityReaction.reaction_type == reaction_type
            ).first()
            if existing:
                db.delete(existing)
            else:
                db.add(CommunityReaction(
                    user_id=user.id,
                    reply_id=target_id,
                    reaction_type=reaction_type
                ))
            db.commit()
            counts, user_reacts = cls._get_reactions_data(db, "reply", target_id, user.id)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_type must be 'post' or 'reply'")

        return {
            "target_type": target_type,
            "target_id": str(target_id),
            "reactions_count": counts,
            "user_reactions": user_reacts
        }

    @classmethod
    def endorse_reply(cls, db: Session, clinician_user: User, reply_id: UUID) -> ReplyResponse:
        if getattr(clinician_user, "role", "") != "clinician":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified pediatric clinicians can endorse community responses."
            )

        reply = db.query(CommunityReply).filter(CommunityReply.id == reply_id).first()
        if not reply:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found")

        # Toggle endorsement
        if reply.is_clinician_endorsed:
            reply.is_clinician_endorsed = False
            reply.endorsed_by_clinician_id = None
        else:
            reply.is_clinician_endorsed = True
            reply.endorsed_by_clinician_id = clinician_user.id

        db.commit()
        db.refresh(reply)

        counts, user_reacts = cls._get_reactions_data(db, "reply", reply.id, clinician_user.id)
        author_name = "Anonymous Caregiver" if reply.is_anonymous else reply.author.username
        endorser_name = clinician_user.username if reply.is_clinician_endorsed else None

        return ReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            author_id=reply.author_id,
            author_name=author_name,
            is_anonymous=reply.is_anonymous,
            author_flair=reply.author_flair,
            is_clinician=getattr(reply.author, "role", "") == "clinician",
            is_clinician_endorsed=reply.is_clinician_endorsed,
            endorsed_by_clinician_name=endorser_name,
            body=reply.body,
            reactions_count=counts,
            user_reactions=user_reacts,
            created_at=reply.created_at
        )
