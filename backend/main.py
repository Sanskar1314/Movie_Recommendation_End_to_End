"""
FastAPI application — Movie Recommendation API.

Loads model artifacts once at startup via the lifespan context manager.
"""

import logging
import os
import sqlite3
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware



from backend import model_loader
from backend.routes.recommend import router as recommend_router
from backend.schemas import HealthResponse
from backend.collaborative import DEFAULT_DATA, ROOT, load_dataset
from backend.store import RatingStore, UnknownProfileError
from backend.routes.personal import PersonalService, router as personal_router
from backend.utils import get_movie_info

# ── Environment & logging ───────────────────────────────────────────
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan — load artifacts once ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model artifacts at startup; nothing to clean up on shutdown."""
    pickle_dir = os.getenv("PICKLE_DIR", None)
    app.state.legacy_ready = False
    try:
        model_loader.load_artifacts(pickle_dir)
        app.state.legacy_ready = True
    except (OSError, ValueError, ImportError):
        logger.exception("Legacy artifacts unavailable; restore trusted pickle_files to enable title discovery.")
    app.state.personal = None
    app.state.personal_error = 'Personal recommendations unavailable. Check server logs.'
    try:
        movies, ratings = load_dataset(os.getenv('MOVIELENS_DIR', str(DEFAULT_DATA)))
        store = RatingStore(os.getenv('RATINGS_DB', str(ROOT / 'data' / 'preferences.sqlite3')))
        app.state.personal = PersonalService(movies, ratings, store)
    except (OSError, ValueError, sqlite3.Error):
        logger.exception('Cannot initialize personal recommendations')
        app.state.personal_error = ('MovieLens unavailable. Run: python scripts/download_movielens.py; '
                                    'check MOVIELENS_DIR and writable RATINGS_DB in server configuration.')
    yield


# ── App initialisation ──────────────────────────────────────────────
app = FastAPI(
    title="MovieMind API",
    description="Personalized collaborative filtering and legacy title similarity.",
    version="2.0.0",
    lifespan=lifespan,
)

# Browser origins for local development; Streamlit calls the API server-side.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────
app.include_router(recommend_router)
app.include_router(personal_router)


@app.exception_handler(UnknownProfileError)
async def unknown_profile(request: Request, exc: UnknownProfileError):
    return JSONResponse(status_code=404, content={'detail': 'Unknown local profile. Create or select a profile first.'})


@app.exception_handler(sqlite3.Error)
async def database_failure(request: Request, exc: sqlite3.Error):
    logger.error('Profile database failure', exc_info=exc)
    return JSONResponse(status_code=503, content={'detail': 'Profile storage unavailable. Check database permissions and retry.'})


@app.middleware('http')
async def legacy_availability(request: Request, call_next):
    path = request.url.path
    if (path in ('/movies', '/movies/popular', '/recommend') or path.startswith('/movie/')) and not getattr(request.app.state, 'legacy_ready', False):
        return JSONResponse(status_code=503, content={'detail': 'Legacy artifacts unavailable. Restore trusted pickle_files or configure PICKLE_DIR.'})
    return await call_next(request)



@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Return API health status."""
    total = len(model_loader.all_titles) if model_loader.all_titles else 0
    return HealthResponse(status="healthy" if app.state.personal is not None and app.state.legacy_ready else "degraded", total_movies=total, personal_ready=app.state.personal is not None, legacy_ready=app.state.legacy_ready)


@app.get("/movies", tags=["Movies"])
async def list_movies():
    """Return the full list of available movie titles (for autocomplete)."""
    return {"total": len(model_loader.all_titles), "titles": model_loader.all_titles}


@app.get("/movies/popular", tags=["Movies"])
async def popular_movies(n: int = Query(60, ge=1, le=100)):
    """Return top N movies sorted by popularity (for homepage grid)."""
    import pandas as pd
    df = model_loader.df.copy()
    df["_pop"] = pd.to_numeric(df["popularity"], errors="coerce").fillna(0)
    top = df.nlargest(n, "_pop")
    return {
        "movies": [
            {"title": str(row["title"]), "popularity": float(row.get("_pop", 0))}
            for _, row in top.iterrows()
        ]
    }


@app.get("/movie/{title}", tags=["Movies"])
async def get_movie(title: str):
    """Return metadata for a single movie by title."""
    info = get_movie_info(title)
    if not info:
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found.")
    return info

