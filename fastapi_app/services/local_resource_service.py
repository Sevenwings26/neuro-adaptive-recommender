# services/local_resource_service.py
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status

from models.auth_models import User
from models.community_models import LocalResource, LocalResourceVote
from schemas.community_schemas import LocalResourceCreate, LocalResourceResponse

log = logging.getLogger(__name__)

SAMPLE_RESOURCES = [
    {
        "name": "We Rock the Spectrum Sensory Gym",
        "category": "sensory_venue",
        "description": "Safe, inclusive indoor sensory gym equipped with suspended swings, crash mats, calming quiet room, and sensory exploration equipment for toddlers and young children.",
        "city": "Austin",
        "state": "TX",
        "address_or_url": "1023 Springdale Rd, Austin, TX",
        "contact_info": "(512) 555-0199",
        "upvotes_count": 18,
        "is_verified": True,
    },
    {
        "name": "BrightSteps Pediatric Speech & OT Clinic",
        "category": "clinic",
        "description": "Multidisciplinary clinic specializing in early toddler language delays, AAC communication devices (Proloquo2Go, TouchChat), and sensory integration occupational therapy.",
        "city": "Austin",
        "state": "TX",
        "address_or_url": "https://brightstepstherapy.example.com",
        "contact_info": "hello@brightsteps.example.com",
        "upvotes_count": 14,
        "is_verified": True,
    },
    {
        "name": "Austin Neurodiversity Caregiver Circle",
        "category": "support_group",
        "description": "Monthly weekend parent-to-parent peer circle. Casual coffee meetups with a safe, sensory-friendly play area for kids. Focus on early screening support and navigating regional centers.",
        "city": "Austin",
        "state": "TX",
        "address_or_url": "Zilker Community Center Room 4",
        "contact_info": "caregivers@austincircle.example.org",
        "upvotes_count": 9,
        "is_verified": True,
    },
    {
        "name": "Early Steps Texas ECI & Grant Assistance",
        "category": "financial_grant",
        "description": "State early childhood intervention guidance, Medicaid waiver navigation, and adaptive equipment mini-grant application clinic for children ages 0-36 months.",
        "city": "Austin",
        "state": "TX",
        "address_or_url": "https://earlystepstx.example.gov",
        "contact_info": "eci-help@texas.example.gov",
        "upvotes_count": 12,
        "is_verified": True,
    },
]


class LocalResourceService:

    @staticmethod
    def seed_default_resources(db: Session, admin_user: Optional[User] = None):
        """Seed starter local resources if table is empty."""
        count = db.query(LocalResource).count()
        if count == 0:
            user = admin_user or db.query(User).first()
            if not user:
                return

            for res_data in SAMPLE_RESOURCES:
                res = LocalResource(
                    submitted_by_id=user.id,
                    name=res_data["name"],
                    category=res_data["category"],
                    description=res_data["description"],
                    city=res_data["city"],
                    state=res_data["state"],
                    address_or_url=res_data["address_or_url"],
                    contact_info=res_data["contact_info"],
                    upvotes_count=res_data["upvotes_count"],
                    is_verified=res_data["is_verified"]
                )
                db.add(res)
            db.commit()
            log.info("✓ Seeded sample Local Resources")

    @staticmethod
    def list_resources(
        db: Session,
        current_user: Optional[User] = None,
        category: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LocalResourceResponse]:
        query = db.query(LocalResource)

        if category and category != "all":
            query = query.filter(LocalResource.category == category)

        if city:
            query = query.filter(LocalResource.city.ilike(f"%{city}%"))

        if state:
            query = query.filter(LocalResource.state.ilike(f"%{state}%"))

        if search_query:
            pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    LocalResource.name.ilike(pattern),
                    LocalResource.description.ilike(pattern),
                    LocalResource.city.ilike(pattern)
                )
            )

        resources = query.order_by(LocalResource.upvotes_count.desc(), LocalResource.created_at.desc()).offset(offset).limit(limit).all()

        current_user_id = current_user.id if current_user else None
        voted_resource_ids = set()
        if current_user_id:
            votes = db.query(LocalResourceVote.resource_id).filter(LocalResourceVote.user_id == current_user_id).all()
            voted_resource_ids = {v[0] for v in votes}

        results = []
        for r in resources:
            results.append(LocalResourceResponse(
                id=r.id,
                name=r.name,
                category=r.category,
                description=r.description,
                city=r.city,
                state=r.state,
                address_or_url=r.address_or_url,
                contact_info=r.contact_info,
                upvotes_count=r.upvotes_count,
                is_verified=r.is_verified,
                submitted_by_name=r.submitted_by.username if r.submitted_by else "Community Member",
                user_has_upvoted=(r.id in voted_resource_ids),
                created_at=r.created_at
            ))
        return results

    @staticmethod
    def create_resource(db: Session, user: User, data: LocalResourceCreate) -> LocalResourceResponse:
        resource = LocalResource(
            submitted_by_id=user.id,
            name=data.name,
            category=data.category,
            description=data.description,
            city=data.city.strip(),
            state=data.state.strip(),
            address_or_url=data.address_or_url,
            contact_info=data.contact_info,
            upvotes_count=1,  # Submitter auto-upvotes
            is_verified=False
        )
        db.add(resource)
        db.flush()

        # Add initial vote from author
        vote = LocalResourceVote(user_id=user.id, resource_id=resource.id)
        db.add(vote)
        db.commit()
        db.refresh(resource)

        return LocalResourceResponse(
            id=resource.id,
            name=resource.name,
            category=resource.category,
            description=resource.description,
            city=resource.city,
            state=resource.state,
            address_or_url=resource.address_or_url,
            contact_info=resource.contact_info,
            upvotes_count=resource.upvotes_count,
            is_verified=resource.is_verified,
            submitted_by_name=user.username,
            user_has_upvoted=True,
            created_at=resource.created_at
        )

    @staticmethod
    def toggle_resource_upvote(db: Session, user: User, resource_id: UUID) -> Dict[str, Any]:
        resource = db.query(LocalResource).filter(LocalResource.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

        existing_vote = db.query(LocalResourceVote).filter(
            LocalResourceVote.user_id == user.id,
            LocalResourceVote.resource_id == resource_id
        ).first()

        if existing_vote:
            db.delete(existing_vote)
            resource.upvotes_count = max(0, resource.upvotes_count - 1)
            user_has_upvoted = False
        else:
            db.add(LocalResourceVote(user_id=user.id, resource_id=resource_id))
            resource.upvotes_count += 1
            user_has_upvoted = True

        db.commit()
        return {
            "resource_id": str(resource_id),
            "upvotes_count": resource.upvotes_count,
            "user_has_upvoted": user_has_upvoted
        }
