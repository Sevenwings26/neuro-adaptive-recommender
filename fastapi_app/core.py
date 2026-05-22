# core.py
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from schemas import RecommendedApp


load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "files/asd_model1.pkl"
MODEL_CARD_PATH = BASE_DIR / "files/model_card1.json"
APP_CACHE_PATH = BASE_DIR / "files/app_cache.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
NEED_MAPPING: dict[tuple, str] = {
    ("A1", "A7"):       "speech delay non-verbal communication words language talk",
    ("A2", "A6", "A8"): "eye contact joint attention gesture social awareness",
    ("A3", "A4", "A5"): "social interaction play cognitive learning pretend",
    ("A9", "A10"):      "sensory processing meltdowns routine calm repetitive behaviour visual",
}

QUESTION_LABELS: dict[str, str] = {
    "A1":  "Responds to name",
    "A2":  "Eye contact",
    "A3":  "Points to indicate wants",
    "A4":  "Points to share interest",
    "A5":  "Pretend play",
    "A6":  "Follows gaze / pointing",
    "A7":  "Uses basic words / speech",
    "A8":  "Understands simple gestures",
    "A9":  "Unusual sensory reactions",
    "A10": "Repetitive or unusual behaviours",
}

GEMINI_MODEL = "models/gemini-2.5-flash"

CHAT_SYSTEM_PROMPT = """\
You are a warm, knowledgeable special education consultant named Nora.
A parent has just received an ASD screening result for their toddler
and wants to understand more about autism and early intervention.

Child's screening context:
- Age        : {age} months
- Sex        : {sex_label}
- ASD Risk   : {risk_probability:.1f}%
- Flags      : {total_flags}/10 milestones flagged
- Flagged    : {flagged_questions}
- Needs      : {profile_text}
- Apps rec.  : {recommended_apps}
"""

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION STATE
# ─────────────────────────────────────────────────────────────────────────────
class AppState:
    model            = None
    model_card       : dict       = {}
    feature_cols     : list[str]  = []

    df_apps          : pd.DataFrame = pd.DataFrame()
    app_tfidf        : Optional[TfidfVectorizer] = None
    app_matrix       = None

    gemini_client    = None
    startup_time     : float = 0.0


state = AppState()


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _load_model() -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    if not MODEL_CARD_PATH.exists():
        raise FileNotFoundError(f"Model card not found: {MODEL_CARD_PATH}")

    state.model = joblib.load(MODEL_PATH)
    with open(MODEL_CARD_PATH, encoding="utf-8") as f:
        state.model_card = json.load(f)
    state.feature_cols = state.model_card.get("feature_columns", [])
    log.info("Model loaded — features: %s", state.feature_cols)


def _fit_tfidf(texts: list[str]) -> tuple[TfidfVectorizer, object]:
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform(texts)
    return vec, matrix


def _load_app_cache() -> None:
    if not APP_CACHE_PATH.exists():
        log.warning("app_cache.json not found.")
        return
    with open(APP_CACHE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    state.df_apps = pd.DataFrame(data)
    texts = state.df_apps["Description"].fillna("").tolist()
    state.app_tfidf, state.app_matrix = _fit_tfidf(texts)
    log.info("App cache loaded — %d apps.", len(state.df_apps))


def _init_gemini() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.warning("GEMINI_API_KEY not set.")
        return
    try:
        from google import genai
        state.gemini_client = genai.Client(api_key=api_key)
        log.info("Gemini client initialized.")
    except Exception as e:
        log.warning("Gemini init failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def build_profile_text(scores: dict[str, int]) -> str:
    needs = [
        phrase for questions, phrase in NEED_MAPPING.items()
        if any(scores.get(q, 0) == 1 for q in questions)
    ]
    return " ".join(needs) if needs else "autism special education cognitive skills"


def predict_risk(scores: dict[str, int]) -> float:
    input_df = pd.DataFrame([{col: scores[col] for col in state.feature_cols}])
    return float(state.model.predict_proba(input_df)[0][1] * 100)


def recommend_apps(profile_text: str, top_n: int) -> list[RecommendedApp]:
    if state.df_apps.empty or state.app_tfidf is None:
        return []
    qvec = state.app_tfidf.transform([profile_text])
    scores = (cosine_similarity(qvec, state.app_matrix).flatten() * 100).round(1)
    df = state.df_apps.copy()
    df["match_score"] = scores
    top = df.sort_values("match_score", ascending=False).head(top_n).reset_index(drop=True)
    
    return [
        RecommendedApp(
            rank=i + 1,
            app_name=row["App_Name"],
            category=row.get("Category", ""),
            rating=float(row.get("Rating", 0)),
            price=row.get("Price", ""),
            description=str(row.get("Description", ""))[:200],
            match_score=float(row["match_score"]),
        )
        for i, row in top.iterrows()
    ]


