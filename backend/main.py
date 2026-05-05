"""
FastAPI application — Movie Recommendation API.

Loads model artifacts once at startup via the lifespan context manager.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware



from backend import model_loader
from backend.routes.recommend import router as recommend_router
from backend.schemas import HealthResponse
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
    model_loader.load_artifacts(pickle_dir)
    yield


# ── App initialisation ──────────────────────────────────────────────
app = FastAPI(
    title="MovieMind API",
    description="AI-powered movie recommendations using TF-IDF & cosine similarity.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow everything for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────
app.include_router(recommend_router)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Return API health status."""
    total = len(model_loader.all_titles) if model_loader.all_titles else 0
    return HealthResponse(status="healthy", total_movies=total)


@app.get("/movies", tags=["Movies"])
async def list_movies():
    """Return the full list of available movie titles (for autocomplete)."""
    return {"total": len(model_loader.all_titles), "titles": model_loader.all_titles}


@app.get("/movies/popular", tags=["Movies"])
async def popular_movies(n: int = 60):
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

