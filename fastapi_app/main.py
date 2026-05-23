# main.py
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import time 

from core import (
    state, _load_model, _load_app_cache, _init_gemini,
    predict_risk, recommend_apps, build_profile_text, QUESTION_LABELS, log
)
from routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up…")
    state.startup_time = time.time()
    _load_model()
    _load_app_cache()
    _init_gemini()
    log.info("Startup complete in %.2fs.", time.time() - state.startup_time)
    yield
    log.info("Shutting down.")

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Neuro-Adaptive ASD Learning Recommender",
    description="ASD early-screening microservice for toddlers...",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)

templates = Jinja2Templates(directory="templates")

# ───────────────────
# WEB UI ENDPOINTS
# ─────────────────
@app.get("/", response_class=HTMLResponse, tags=["UI"])
def index(request: Request):
    """Render the screening form."""
    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "model_card" : state.model_card,
            "apps_count" : len(state.df_apps),
        },
    )


@app.post("/screen", response_class=HTMLResponse, tags=["UI"])
async def screen(
    request: Request,
    age: int = Form(...), sex: int = Form(...),
    A1: int = Form(...), A2: int = Form(...), A3: int = Form(...),
    A4: int = Form(...), A5: int = Form(...), A6: int = Form(...),
    A7: int = Form(...), A8: int = Form(...), A9: int = Form(...),
    A10: int = Form(...),
    top_n: int = Form(3),
):    
    """Process the form, run inference, render results page."""
    scores = {
        "A1": A1, "A2": A2, "A3": A3, "A4": A4, "A5": A5,
        "A6": A6, "A7": A7, "A8": A8, "A9": A9, "A10": A10,
        "Sex": sex,
    }
 
        

    risk = predict_risk(scores)
    high_risk = risk >= 50.0
    total_flags = sum(v for k, v in scores.items() if k.startswith("A"))
    profile_text = build_profile_text(scores) if high_risk else ""

    app_recs = recommend_apps(profile_text, top_n) if high_risk else []

    flagged_details = [
        {"code": k, "label": QUESTION_LABELS[k]}
        for k in QUESTION_LABELS if scores.get(k, 0) == 1
    ]

    screening_context = {
        "age": age,
        "sex_label": "Male" if sex == 1 else "Female",
        "risk_probability": round(risk, 1),
        "total_flags": total_flags,
        "flagged_questions": [f"{d['code']}: {d['label']}" for d in flagged_details],
        "recommended_apps": [r.app_name for r in app_recs],
        "profile_text": profile_text,
    }

    return templates.TemplateResponse(
        request,
        "results.html",
        context={
            "age": age,
            "sex_label": "Male" if sex == 1 else "Female",
            "risk_probability": round(risk, 1),
            "high_risk": high_risk,
            "total_flags": total_flags,
            "flagged_details": flagged_details,
            "profile_text": profile_text,
            "recommendations": app_recs,
            "model_card": state.model_card,
            "screening_context": json.dumps(screening_context),
            "chat_available": state.gemini_client is not None,
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

