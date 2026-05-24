# main.py
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import time 
import traceback
import os
from dotenv import load_dotenv
import sys

from core import (
    state, _load_model, _load_app_cache, _init_gemini, 
    # _download_if_missing, 
    predict_risk, recommend_apps, build_profile_text, explain_profile, QUESTION_LABELS, log
)
from routers import api_router

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# load_dotenv()

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     log.info("Starting up…")
#     state.startup_time = time.time()
    
#     try:
#         _load_model()
#         log.info("✓ Model loaded")
        
#         # _download_if_missing() 
#         # log.info("✓ files downloaded loaded")

#         _load_app_cache()
#         log.info("✓ App cache loaded")
        
#         _init_gemini()
#         log.info(f"✓ Gemini client initialized: {state.gemini_client is not None}")
        
#         # Verify API key is loaded
#         load_dotenv()
#         api_key = os.getenv("GEMINI_API_KEY")
#         log.info(f"GEMINI_API_KEY from env: {'✓ Present' if api_key else '✗ Missing'}")
        
#     except Exception as e:
#         log.error(f"Startup error: {e}")
#         # Don't raise - allow app to start but with limited functionality
    
#     log.info(f"Startup complete in {time.time() - state.startup_time:.2f}s")
#     log.info(f"Chat available: {state.gemini_client is not None}")
    
#     yield
    
#     log.info("Shutting down.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up Neuro-Adaptive ASD Recommender...")

    state.startup_time = time.time()
    startup_success = True

    try:
        # Load environment variables (best done early)
        load_dotenv(override=True)

        _load_model()
        log.info("✓ Model loaded successfully")

        _load_app_cache()
        log.info(f"✓ App cache loaded — {len(state.df_apps)} apps")

        _init_gemini()
        log.info(f"✓ Gemini initialized: {state.gemini_client is not None}")

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            log.warning("⚠️ GEMINI_API_KEY is missing — Chat feature will be disabled")

    except Exception as e:
        log.error(f"❌ Critical startup error: {e}")
        startup_success = False
        # In production, you may choose to raise here for fail-fast behavior
        # raise  # Uncomment in strict production mode

    log.info(f"Startup completed in {time.time() - state.startup_time:.2f}s")
    log.info(f"Chat available: {state.gemini_client is not None}")
    log.info(f"Overall startup success: {startup_success}")

    yield

    log.info("Shutting down.")


# ──────────────────────────
# FASTAPI APP
# ─────────────────────────────
app = FastAPI(
    title="Neuro-Adaptive ASD Learning Recommender",
    description="ASD early-screening microservice for toddlers...",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)

templates = Jinja2Templates(directory="templates")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("=== UNHANDLED EXCEPTION ===")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def index(request: Request):
    """Render the screening form."""
    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "model_card"    : state.model_card,
            "apps_count"    : len(state.df_apps),
            "chat_available": state.gemini_client is not None,  
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

    try:
        log.info(f"Processing screen request: age={age}, sex={sex}, top_n={top_n}")
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
        app_recs     = recommend_apps(profile_text, top_n) if high_risk else []

        profile_explained = ""
        if state.gemini_client:
            try:
                profile_explained = await explain_profile(
                    age              = age,
                    sex_label        = "Male" if sex == 1 else "Female",
                    risk_probability = round(risk, 1),
                    total_flags      = total_flags,
                    flagged_details  = flagged_details,
                    profile_text     = profile_text,
                    gemini_client    = state.gemini_client,
                )
            except Exception as e:
                log.error("explain_profile crashed: %s", e)
                profile_explained = "We recommend focusing on communication and social engagement activities."

        # profile_explained = ""
        # if state.gemini_client:
        #     try:
        #         profile_explained = await explain_profile(
        #             profile_text=profile_text,
        #             age=age,
        #             sex_label="Male" if sex == 1 else "Female",
        #             gemini_client=state.gemini_client,
        #         )
        #     except Exception as e:
        #         log.error(f"explain_profile crashed: {e}")
        #         profile_explained = "We recommend focusing on communication and social engagement activities."
                
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
            "profile_explained": profile_explained, # human-readable — shown in UI
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
                "profile_explained": profile_explained,
                "recommendations": app_recs,
                "model_card": state.model_card,
                "screening_context": json.dumps(screening_context),
                "chat_available": state.gemini_client is not None,
            },
        )
        
    except Exception as e:
        # Get full traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        full_traceback = "".join(tb_lines)
        
        # Log to both file and console
        log.error(f"SCREEN ENDPOINT FAILED:\n{full_traceback}")
        
        # Print to stderr as well (uvicorn will capture this)
        print(f"\n{'='*80}\nERROR IN /screen:\n{full_traceback}\n{'='*80}\n", 
              file=sys.stderr)
        

@app.get("/apps-page", response_class=HTMLResponse, tags=["UI"])
def apps_page(request: Request):
    """Render the apps catalogue page."""
    try:
        # Get the apps data
        if state.df_apps.empty:
            apps_list = []
            total = 0
        else:
            apps_list = []
            for _, row in state.df_apps.iterrows():
                apps_list.append({
                    "app_name": row["App_Name"],
                    "category": row.get("Category", "Uncategorized"),
                    "rating": float(row.get("Rating", 0)),
                    "price": row.get("Price", "Free"),
                    "description": row.get("Description", "No description available.")[:200],
                })
            total = len(apps_list)
        
        log.info(f"Rendering apps page with {total} apps")
        
        return templates.TemplateResponse(
            request,
            "all_apps.html",
            context={
                "apps": apps_list,
                "total_apps": total,
                "chat_available": state.gemini_client is not None,
            },
        )
    except Exception as e:
        log.error(f"Error rendering apps page: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h1>Error</h1><pre>{str(e)}</pre>", status_code=500)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)



