"""
schemas.py — Pydantic models for all API request/response bodies.

Having schemas in a separate file means:
  - main.py stays readable
  - FastAPI auto-generates accurate OpenAPI docs from these types
  - The Streamlit app can import them too for type-safe calls
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# SHARED VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def _binary(v: int) -> int:
    if v not in (0, 1):
        raise ValueError("Must be 0 or 1.")
    return v


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class BehavioralProfile(BaseModel):
    """
    Q-CHAT-10 behavioral screening profile for a toddler.

    All A-fields are binary:
      0 = typical milestone met
      1 = milestone delayed / not observed

    Sex: 1 = Male, 0 = Female
    """

    A1  : int = Field(..., ge=0, le=1, description="Responds to name when called")
    A2  : int = Field(..., ge=0, le=1, description="Makes eye contact")
    A3  : int = Field(..., ge=0, le=1, description="Points to indicate wants")
    A4  : int = Field(..., ge=0, le=1, description="Points to share interest")
    A5  : int = Field(..., ge=0, le=1, description="Engages in pretend play")
    A6  : int = Field(..., ge=0, le=1, description="Follows gaze / pointing")
    A7  : int = Field(..., ge=0, le=1, description="Uses basic words or speech")
    A8  : int = Field(..., ge=0, le=1, description="Understands simple gestures")
    A9  : int = Field(..., ge=0, le=1, description="Unusual sensory reactions (1 = present)")
    A10 : int = Field(..., ge=0, le=1, description="Repetitive or unusual behaviours (1 = present)")
    Sex : int = Field(..., ge=0, le=1, description="Biological sex: 1 = Male, 0 = Female")

    @field_validator("A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","Sex")
    @classmethod
    def must_be_binary(cls, v: int) -> int:
        return _binary(v)

    model_config = {
        "json_schema_extra": {
            "example": {
                "A1": 1, "A2": 0, "A3": 1, "A4": 1, "A5": 0,
                "A6": 1, "A7": 1, "A8": 0, "A9": 1, "A10": 1,
                "Sex": 1,
            }
        }
    }


class PredictRequest(BehavioralProfile):
    """Request body for POST /predict."""
    pass


class RecommendRequest(BehavioralProfile):
    """Request body for POST /recommend."""
    top_n: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of app recommendations to return (1–10).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "A1": 1, "A2": 1, "A3": 1, "A4": 1, "A5": 1,
                "A6": 1, "A7": 1, "A8": 1, "A9": 1, "A10": 1,
                "Sex": 1,
                "top_n": 3,
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class PredictResponse(BaseModel):
    """Response body for POST /predict."""
    risk_probability  : float = Field(..., description="ASD trait probability 0–100%")
    high_risk         : bool  = Field(..., description="True if probability ≥ 50%")
    total_flags       : int   = Field(..., description="Number of Q-CHAT questions flagged")
    flagged_questions : list[str] = Field(..., description="Human-readable list of flagged milestones")
    latency_ms        : float = Field(..., description="Inference latency in milliseconds")


class RecommendedApp(BaseModel):
    """A single ranked app recommendation."""
    rank        : int
    app_name    : str
    category    : str
    rating      : float
    price       : str
    description : str
    match_score : float = Field(..., description="TF-IDF cosine similarity score 0–100")


class RecommendResponse(BaseModel):
    """Response body for POST /recommend."""
    risk_probability : float
    high_risk        : bool
    total_flags      : int
    profile_text     : str  = Field(..., description="Semantic need-query derived from behavioral profile")
    recommendations  : list[RecommendedApp]
    message          : str
    latency_ms       : float


class AppItem(BaseModel):
    """A single app from the cache."""
    app_name    : str
    category    : str
    rating      : float
    price       : str
    description : str


class AppsResponse(BaseModel):
    """Response body for GET /apps."""
    total : int
    apps  : list[AppItem]


class BookItem(BaseModel):
    """A single book from book_cache.json."""
    title       : str
    author      : str
    category    : str
    age_range   : str
    description : str
    access      : str = Field(..., description="'free' or 'paid'")
    free_url    : Optional[str] = None
    paid_url    : Optional[str] = None
    cover_emoji : str = "📖"


class BookRecommendation(BookItem):
    """A ranked book recommendation with match score."""
    rank        : int
    match_score : float = Field(..., description="TF-IDF cosine similarity 0–100")


class BooksResponse(BaseModel):
    """Response body for GET /books."""
    total : int
    books : list[BookItem]


class RecommendedApp(BaseModel):
    """A single ranked app recommendation."""
    rank        : int
    app_name    : str
    category    : str
    rating      : float
    price       : str
    description : str
    match_score : float = Field(..., description="TF-IDF cosine similarity score 0–100")


class RecommendResponse(BaseModel):
    """Response body for POST /recommend."""
    risk_probability    : float
    high_risk           : bool
    total_flags         : int
    profile_text        : str  = Field(..., description="Semantic need-query derived from behavioral profile")
    recommendations     : list[RecommendedApp]
    book_recommendations: list[BookRecommendation]
    message             : str
    latency_ms          : float


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status         : str
    model_loaded   : bool
    model_type     : str
    test_accuracy  : float
    test_roc_auc   : float
    feature_cols   : list[str]
    apps_in_cache  : int
    books_in_cache : int
    uptime_seconds : float


# ─────────────────────────────────────────────────────────────────────────────
# CHAT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ScreeningContext(BaseModel):
    """
    Snapshot of the child's screening result — sent with every chat message
    so Gemini always has personalised context without server-side session state.
    """
    age               : int
    sex_label         : str
    risk_probability  : float
    total_flags       : int
    flagged_questions : list[str]
    recommended_apps  : list[str]   = Field(default_factory=list)
    recommended_books : list[str]   = Field(default_factory=list)
    profile_text      : str         = ""


class ChatMessage(BaseModel):
    role    : str = Field(..., description="'user' or 'assistant'")
    content : str


class ChatRequest(BaseModel):
    """Request body for POST /chat."""
    screening_context : ScreeningContext
    history           : list[ChatMessage] = Field(
        default_factory=list,
        description="Full conversation history (all prior turns). Max 20 turns.",
    )
    message           : str = Field(..., min_length=1, max_length=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "screening_context": {
                    "age": 24,
                    "sex_label": "Male",
                    "risk_probability": 87.4,
                    "total_flags": 7,
                    "flagged_questions": ["A1: Responds to name", "A7: Basic speech"],
                    "recommended_apps": ["Otsimo Special Education", "Proloquo2Go"],
                    "recommended_books": ["More Than Words", "An Early Start for Your Child with Autism"],
                    "profile_text": "speech delay non-verbal communication words language"
                },
                "history": [],
                "message": "What does the speech delay score mean for my child's development?"
            }
        }
    }


class ChatResponse(BaseModel):
    """Response body for POST /chat."""
    reply      : str
    latency_ms : float

    