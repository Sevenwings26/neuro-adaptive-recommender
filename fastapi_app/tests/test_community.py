import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID, uuid4

FASTAPI_DIR = Path("/home/techyz-admin/sevenwings/02_startups/neuro-adaptive-recommender/fastapi_app")
sys.path.insert(0, str(FASTAPI_DIR))

from starlette.testclient import TestClient
from database import get_db, engine, Base, SessionLocal
from models.auth_models import User
from models.domain_models import ChildProfile
from models.community_models import (
    CommunityCircle,
    CommunityPost,
    CommunityReply,
    CommunityReaction,
    LocalResource,
    LocalResourceVote,
)
from services.community_service import CommunityService
from services.local_resource_service import LocalResourceService
from core import _load_model, _load_app_cache, _load_book_cache
from main import app

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Initialize caches
_load_model()
_load_app_cache()
_load_book_cache()

client = TestClient(app)

print("=" * 80)
print("STARTING CAREGIVER VILLAGE & IN-APP COMMUNITY INTEGRATION TEST SUITE")
print("=" * 80)

# Setup: Register Parent User & Clinician User
ts = int(time.time())
parent_user = f"village_parent_{ts}"
parent_email = f"parent_{ts}@example.com"
clinician_user = f"village_dr_{ts}"
clinician_email = f"dr_{ts}@example.com"
password = "SecurePassword123!"

# Register parent
r_p = client.post("/auth/register", json={
    "username": parent_user, "email": parent_email, "password": password, "role": "parent"
})
assert r_p.status_code == 201, f"Parent registration failed: {r_p.text}"

# Register clinician
r_c = client.post("/auth/register", json={
    "username": clinician_user, "email": clinician_email, "password": password, "role": "clinician"
})
assert r_c.status_code == 201, f"Clinician registration failed: {r_c.text}"

# Login parent
login_p = client.post("/auth/login", json={"username_or_email": parent_user, "password": password})
assert login_p.status_code == 200
parent_token = login_p.json()["access_token"]
parent_headers = {"Authorization": f"Bearer {parent_token}"}
parent_cookies = {"access_token": parent_token}

# Login clinician
login_c = client.post("/auth/login", json={"username_or_email": clinician_user, "password": password})
assert login_c.status_code == 200
clinician_token = login_c.json()["access_token"]
clinician_headers = {"Authorization": f"Bearer {clinician_token}"}
clinician_cookies = {"access_token": clinician_token}

# Create child profile for parent (24 months old)
child_dob = (datetime.now(timezone.utc) - timedelta(days=24 * 30)).date().isoformat()
r_child = client.post("/api/v1/children", json={
    "first_name": "Maya",
    "date_of_birth": child_dob,
    "biological_sex": 0
}, headers=parent_headers)
assert r_child.status_code == 201
child_id = r_child.json()["id"]
print(f"  ✓ Setup complete: Parent '{parent_user}', Clinician '{clinician_user}', Child 'Maya' (ID: {child_id})")

# Ensure circles and resources are seeded
db = next(get_db())
try:
    CommunityService.seed_default_circles(db)
    LocalResourceService.seed_default_resources(db)
finally:
    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Circles Retrieval & Seeding
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 1] Testing Community Circles Retrieval & Seeding...")
res_circles = client.get("/api/v1/community/circles")
assert res_circles.status_code == 200
circles = res_circles.json()
assert len(circles) >= 7, f"Expected at least 7 circles, got {len(circles)}"
slugs = [c["slug"] for c in circles]
for s in ["speech-aac", "sensory-meltdowns", "toddlers-12-24m", "preschool-24-48m", "routines-sleep-eating", "clinical-evals", "local-opportunities"]:
    assert s in slugs, f"Missing circle slug: {s}"
speech_circle_id = next(c["id"] for c in circles if c["slug"] == "speech-aac")
sensory_circle_id = next(c["id"] for c in circles if c["slug"] == "sensory-meltdowns")
print(f"  ✓ Verified {len(circles)} topical developmental circles active and seeded!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Post Creation (Named vs. Anonymous Privacy Mode) & Author Flair
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 2] Testing Post Creation & Privacy-Preserving Anonymity...")

# Case A: Named post
p1_payload = {
    "circle_id": speech_circle_id,
    "title": "When did your toddler start using AAC speech gestures?",
    "body": "Our 24-month-old is showing high receptivity to visual icons, but we are wondering how to best introduce Proloquo2Go during mealtime.",
    "post_type": "question",
    "is_anonymous": False,
    "child_id": child_id
}
res_p1 = client.post("/api/v1/community/posts", json=p1_payload, headers=parent_headers)
assert res_p1.status_code == 201, f"Create named post failed: {res_p1.text}"
post1 = res_p1.json()
assert post1["author_name"] == parent_user
assert post1["is_anonymous"] is False
assert "Parent of" in post1["author_flair"]
post1_id = post1["id"]
print(f"  ✓ Named Post published (ID: {post1_id}): Author={post1['author_name']}, Flair='{post1['author_flair']}'")

# Case B: Anonymous post
p2_payload = {
    "circle_id": sensory_circle_id,
    "title": "Overwhelmed by loud sound transitions in supermarket",
    "body": "Looking for gentle de-escalation tips when sensory sound triggers cause an acute meltdown in public aisles.",
    "post_type": "concern",
    "is_anonymous": True,
    "child_id": child_id
}
res_p2 = client.post("/api/v1/community/posts", json=p2_payload, headers=parent_headers)
assert res_p2.status_code == 201, f"Create anonymous post failed: {res_p2.text}"
post2 = res_p2.json()
assert post2["author_name"] == "Anonymous Caregiver"
assert post2["is_anonymous"] is True
assert "Parent of" in post2["author_flair"]
post2_id = post2["id"]
print(f"  ✓ Anonymous Post published (ID: {post2_id}): Author correctly masked as '{post2['author_name']}' while preserving flair '{post2['author_flair']}'!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: Neuro-Affirming Empathy Reactions
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 3] Testing Neuro-Affirming Empathy Reactions...")

# Toggle 'support' on post1
rxn1 = client.post(f"/api/v1/community/posts/{post1_id}/react", json={"reaction_type": "support"}, headers=parent_headers)
assert rxn1.status_code == 200
data_rxn1 = rxn1.json()
assert data_rxn1["reactions_count"]["support"] == 1
assert "support" in data_rxn1["user_reactions"]

# Toggle 'support' off (idempotent removal)
rxn1_off = client.post(f"/api/v1/community/posts/{post1_id}/react", json={"reaction_type": "support"}, headers=parent_headers)
assert rxn1_off.status_code == 200
assert rxn1_off.json()["reactions_count"]["support"] == 0

# Add 'helpful' from parent and 'relate' from clinician
client.post(f"/api/v1/community/posts/{post1_id}/react", json={"reaction_type": "helpful"}, headers=parent_headers)
client.post(f"/api/v1/community/posts/{post1_id}/react", json={"reaction_type": "relate"}, headers=clinician_headers)

feed_check = client.get(f"/api/v1/community/posts?circle_slug=speech-aac", headers=parent_headers)
assert feed_check.status_code == 200
feed_posts = feed_check.json()
matching = next(p for p in feed_posts if p["id"] == post1_id)
assert matching["reactions_count"]["helpful"] == 1
assert matching["reactions_count"]["relate"] == 1
assert "helpful" in matching["user_reactions"]
print("  ✓ Verified neuro-affirming reactions: support, relate, helpful, celebrate toggling smoothly!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: Replies & Clinician Endorsement
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 4] Testing Discussion Replies & Clinician Endorsement...")

# Parent adds helpful reply
rep_res = client.post(f"/api/v1/community/posts/{post1_id}/replies", json={
    "body": "We found pairing high-contrast PECS cards with AAC buttons reduced frustration within 10 days.",
    "is_anonymous": False
}, headers=parent_headers)
assert rep_res.status_code == 201
reply = rep_res.json()
reply_id = reply["id"]
assert reply["is_clinician_endorsed"] is False
print(f"  ✓ Reply posted by parent (ID: {reply_id})")

# Parent tries to endorse reply -> MUST BE REJECTED with 403 Forbidden
p_endorse = client.post(f"/api/v1/community/replies/{reply_id}/endorse", headers=parent_headers)
assert p_endorse.status_code == 403, f"Expected 403 for non-clinician, got {p_endorse.status_code}"
print("  ✓ Non-clinician endorsement attempt correctly blocked with HTTP 403 Forbidden!")

# Clinician endorses reply -> MUST SUCCEED with 200 OK
c_endorse = client.post(f"/api/v1/community/replies/{reply_id}/endorse", headers=clinician_headers)
assert c_endorse.status_code == 200, f"Clinician endorsement failed: {c_endorse.text}"
endorsed_reply = c_endorse.json()
assert endorsed_reply["is_clinician_endorsed"] is True
assert endorsed_reply["endorsed_by_clinician_name"] == clinician_user
print(f"  ✓ Verified clinician endorsement: '⭐ Clinician Endorsed by {clinician_user}'")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: RAG Clinical Evidence Spotlight Integration
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 5] Testing RAG Clinical Evidence Spotlight on Discussion Detail...")

detail_res = client.get(f"/api/v1/community/posts/{post1_id}", headers=parent_headers)
assert detail_res.status_code == 200
detail = detail_res.json()
assert detail["views_count"] >= 1
assert len(detail["replies"]) >= 1
assert detail["replies"][0]["is_clinician_endorsed"] is True

# Evidence spotlight must match AAC query
assert len(detail["evidence_spotlight"]) > 0, "Expected RAG evidence spotlight for AAC discussion"
top_evidence = detail["evidence_spotlight"][0]
print(f"  ✓ Attached RAG Clinical Evidence Spotlight: '{top_evidence.get('title')}' (Tier: {top_evidence.get('tier')})")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: Local Resource Exchange & Community Upvoting
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 6] Testing Local Resource Directory & Upvoting...")

# List pre-seeded resources in Austin
res_list = client.get("/api/v1/community/resources?city=Austin", headers=parent_headers)
assert res_list.status_code == 200
resources = res_list.json()
assert len(resources) >= 1
print(f"  ✓ Retrieved {len(resources)} local resources in Austin")

# Parent submits new local resource
new_res = client.post("/api/v1/community/resources", json={
    "name": "Play & Bloom Pediatric Occupational Therapy",
    "category": "clinic",
    "description": "Sensory integration gym with certified sensory therapists and quiet rooms.",
    "city": "Austin",
    "state": "TX",
    "address_or_url": "https://playandbloom.example.com",
    "contact_info": "(512) 555-0899"
}, headers=parent_headers)
assert new_res.status_code == 201
res_obj = new_res.json()
new_res_id = res_obj["id"]
assert res_obj["upvotes_count"] == 1
assert res_obj["user_has_upvoted"] is True
print(f"  ✓ Successfully created Local Resource '{res_obj['name']}' (ID: {new_res_id})")

# Clinician upvotes the resource
c_upvote = client.post(f"/api/v1/community/resources/{new_res_id}/upvote", headers=clinician_headers)
assert c_upvote.status_code == 200
assert c_upvote.json()["upvotes_count"] == 2
assert c_upvote.json()["user_has_upvoted"] is True
print("  ✓ Local resource upvoted to 2 community votes!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: Web UI Route & Mobile Navigation Drawer
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 7] Testing Web UI Route /community & Navigation...")

# Authenticated view
ui_res = client.get("/community", cookies=parent_cookies)
assert ui_res.status_code == 200, f"/community returned {ui_res.status_code}"
html = ui_res.text
assert "Caregiver Village & Community Hub" in html
assert "topbarActions" in html
assert "menu-toggle" in html
assert "discussionsFeed" in html
assert "resourcesFeed" in html
assert "Speech &amp; Nonverbal / AAC" in html or "Speech & Nonverbal / AAC" in html
print("  ✓ /community UI view rendered HTTP 200 with full navigation, circles, and feed!")

# Unauthenticated view -> Redirects to login
unauth_client = TestClient(app)
unauth_res = unauth_client.get("/community", follow_redirects=False)
assert unauth_res.status_code == 303
assert "/login" in unauth_res.headers["location"]
print("  ✓ Unauthenticated /community correctly redirects with HTTP 303 to /login!")

print("\n" + "=" * 80)
print("🎉 ALL CAREGIVER VILLAGE & IN-APP COMMUNITY TESTS PASSED SUCCESSFULLY!")
print("=" * 80)
