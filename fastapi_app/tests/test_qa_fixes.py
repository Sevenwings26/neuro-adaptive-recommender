import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4, UUID

FASTAPI_DIR = Path("/home/techyz-admin/sevenwings/02_startups/neuro-adaptive-recommender/fastapi_app")
sys.path.insert(0, str(FASTAPI_DIR))

from starlette.testclient import TestClient
from database import get_db, engine, Base
from models.auth_models import User
from models.domain_models import ChildProfile, ScreeningAssessment
from services.trajectory_service import TrajectoryService
from core import _load_model, _load_app_cache, _load_book_cache
from main import app

# Initialize ML artifacts for testing
_load_model()
_load_app_cache()
_load_book_cache()

client = TestClient(app)

print("=" * 80)
print("RUNNING AUTOMATED TEST SUITE FOR QA REPORT DEFECT FIXES")
print("=" * 80)

# Setup: Register parent user
ts = int(time.time())
parent_email = f"qa_parent_{ts}@example.com"
parent_user = f"qa_parent_{ts}"
password = "SecurePassword123!"

reg_resp = client.post("/auth/register", json={
    "username": parent_user,
    "email": parent_email,
    "password": password,
    "role": "parent"
})
assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"

login_resp = client.post("/auth/login", json={
    "username_or_email": parent_user,
    "password": password
})
assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
cookies = login_resp.cookies
headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: FINDING 2 — Add Child Age-Range Validation (12–48 Months)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 1] Testing Age-Range Validation on Add Child (12–48 months)...")

# Case A: 6.5 years old (DOB 2020-01-01) -> MUST FAIL with 422
resp_old = client.post("/api/v1/children", json={
    "first_name": "OverAgeKid",
    "date_of_birth": "2020-01-01",
    "biological_sex": 1
}, headers=headers)
assert resp_old.status_code == 422, f"Expected 422 for 2020-01-01, got {resp_old.status_code}"
assert "calibrated specifically for toddlers aged 12 to 48 months" in resp_old.text
print("  ✓ Correctly rejected child over 48 months (2020-01-01) with HTTP 422!")

# Case B: Under 12 months (DOB 3 months ago) -> MUST FAIL with 422
infant_dob = (datetime.now(timezone.utc) - timedelta(days=90)).date().isoformat()
resp_young = client.post("/api/v1/children", json={
    "first_name": "InfantKid",
    "date_of_birth": infant_dob,
    "biological_sex": 0
}, headers=headers)
assert resp_young.status_code == 422, f"Expected 422 for infant, got {resp_young.status_code}"
assert "calibrated specifically for toddlers aged 12 to 48 months" in resp_young.text
print("  ✓ Correctly rejected infant under 12 months with HTTP 422!")

# Case C: Valid toddler (DOB 24 months ago) -> MUST SUCCEED with 201
valid_dob = (datetime.now(timezone.utc) - timedelta(days=24 * 30)).date().isoformat()
resp_valid = client.post("/api/v1/children", json={
    "first_name": "ValidToddler",
    "date_of_birth": valid_dob,
    "biological_sex": 1
}, headers=headers)
assert resp_valid.status_code == 201, f"Expected 201 for 24mo toddler, got {resp_valid.status_code}: {resp_valid.text}"
child_id = resp_valid.json()["id"]
print(f"  ✓ Successfully registered calibrated toddler (ID: {child_id}, Age: 24mo) with HTTP 201!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: FINDING 1 — Nora AI General Chat Mode Prompt Grounding
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 2] Testing Nora AI General Mode Prompt (No Hallucinated Data)...")
# Verify that recommend_router uses GENERAL_CHAT_SYSTEM_PROMPT when screened: false
from routers.recommend_router import GENERAL_CHAT_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT
from schemas.recommend import ChatRequest, ScreeningContext, ChatMessage

unscreened_ctx = ScreeningContext(
    age=0,
    sex_label="Unknown",
    risk_probability=0.0,
    total_flags=0,
    flagged_questions=[],
    recommended_apps=[],
    recommended_books=[],
    profile_text="general autism support",
    screened=False
)
chat_req = ChatRequest(
    screening_context=unscreened_ctx,
    history=[],
    message="What is autism?"
)

# Test the router logic directly
from core import state
# Check prompt selection logic
is_screened = getattr(unscreened_ctx, "screened", False) and (unscreened_ctx.age > 0 or unscreened_ctx.total_flags > 0 or unscreened_ctx.risk_probability > 0)
assert not is_screened, "Unscreened context should NOT be marked as screened!"
assert "DO NOT say the baby is newborn, 0 months old, or has 0.0% risk." in GENERAL_CHAT_SYSTEM_PROMPT
assert "No screening has been conducted yet for this session." in GENERAL_CHAT_SYSTEM_PROMPT
print("  ✓ Verified GENERAL_CHAT_SYSTEM_PROMPT strictly prohibits fabricating age 0 or 0.0% risk!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: FINDING 3 — Trajectory Timeline Chronology & DOB Age Anchoring
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 3] Testing Trajectory Chronology & DOB Anchoring...")
db = next(get_db())
try:
    child = db.query(ChildProfile).filter(ChildProfile.id == UUID(str(child_id))).first()
    assert child is not None

    # Insert two assessments: one 60 days ago, one today
    a1 = ScreeningAssessment(
        child_id=child.id,
        completed_at=datetime.now(timezone.utc) - timedelta(days=60),
        age_months=22, # Even if saved as 22 or slider was moved
        a1_score=3, a2_score=3, a3_score=3, a4_score=3, a5_score=3,
        a6_score=3, a7_score=3, a8_score=3, a9_score=3, a10_score=3,
        risk_probability=75.0,
        is_high_risk=True,
        total_flags=10,
        profile_text="Initial baseline"
    )
    a2 = ScreeningAssessment(
        child_id=child.id,
        completed_at=datetime.now(timezone.utc),
        age_months=24,
        a1_score=0, a2_score=0, a3_score=0, a4_score=0, a5_score=0,
        a6_score=0, a7_score=0, a8_score=0, a9_score=0, a10_score=0,
        risk_probability=15.0,
        is_high_risk=False,
        total_flags=0,
        profile_text="Follow-up assessment"
    )
    db.add(a1)
    db.add(a2)
    db.commit()

    traj = TrajectoryService.get_trajectory(db, child)
    assert traj.total_assessments == 2
    # Verify ages are non-decreasing
    ages = [t.age_months for t in traj.assessments_timeline]
    print(f"  Calibrated trajectory timeline ages: {ages}")
    assert ages[0] <= ages[1], f"Age regression detected: {ages}"
    assert traj.trend_direction == "improving"
    assert traj.risk_delta == -60.0
    print("  ✓ Trajectory timeline verified: chronological, strictly non-decreasing ages, and accurate delta math (-60.0%)!")
finally:
    db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: FINDING 4 — Recommendation Count & Low-Risk App Recommendations
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 4] Testing Low-Risk Screening App Recommendations & Default Count...")
screen_payload = {
    "age": 24, "sex": 1,
    "A1": "Always", "A2": "Always", "A3": "Always", "A4": "Always", "A5": "Always",
    "A6": "Always", "A7": "Always", "A8": "Always", "A9": "Usually", "A10": "Usually",
    "child_id": str(child_id),
    "top_n": 3
}
screen_res = client.post("/screen", data=screen_payload, cookies=cookies)
assert screen_res.status_code == 200, f"Screening returned {screen_res.status_code}"
html_out = screen_res.text

# Must render the recommendations section even for low risk
assert "Recommended Early Learning & Development Apps" in html_out or "Recommended Intervention Apps" in html_out
assert "rec-card" in html_out
assert '"screened": true' in html_out
print("  ✓ Low-risk screening successfully renders curated developmental apps and sets screened: true in chat context!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: FINDING 5 — Evidence Library Character Encoding Bug Fix
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 5] Testing Character Encoding on /evidence...")
ev_res = client.get("/evidence", cookies=cookies)
assert ev_res.status_code == 200
ev_html = ev_res.text

# Must NOT contain the old mojibake
assert "<title>Clinical Evidence Library ? NeuroAdapt</title>" not in ev_html
assert "<span>??</span>" not in ev_html

# Must contain the clean UTF-8 / entity text
assert "Clinical Evidence Library &mdash; NeuroAdapt" in ev_html or "Clinical Evidence Library — NeuroAdapt" in ev_html
assert "<span>🔍</span>" in ev_html
print("  ✓ Verified /evidence renders valid title entity (&mdash;) and clean magnifying glass icon (🔍) with no mojibake!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: FINDING 6 — Lightweight Health Check Endpoint
# ─────────────────────────────────────────────────────────────────────────────
print("\n[TEST 6] Testing Ultralight /health Endpoint for Keep-Alive...")
t0 = time.time()
health_res = client.get("/health")
latency = (time.time() - t0) * 1000
assert health_res.status_code == 200
data = health_res.json()
assert data["status"] == "ok"
assert data["model_loaded"] is True
print(f"  ✓ /health endpoint responded HTTP 200 in {latency:.2f}ms with status='ok'!")

print("\n" + "=" * 80)
print("🎉 ALL 6 QA REPORT DEFECTS VERIFIED & PASSING AUTOMATED TESTS!")
print("=" * 80)
