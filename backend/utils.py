"""
Utility functions — core recommendation logic.

Keeps route handlers thin by centralising the cosine-similarity
computation and result formatting here.
"""

from __future__ import annotations

import logging
from difflib import get_close_matches

from sklearn.metrics.pairwise import cosine_similarity

from backend import model_loader

logger = logging.getLogger(__name__)


def resolve_title(raw_title: str) -> str | None:
    """Resolve a user-supplied title to the canonical title in the index.

    Tries exact match first, then case-insensitive, then fuzzy.

    Returns:
        The canonical title string, or ``None`` if no match found.
    """
    # 1. Exact match
    if raw_title in model_loader.indices:
        return raw_title

    # 2. Case-insensitive match
    lower = raw_title.strip().lower()
    if lower in model_loader.title_lookup:
        return model_loader.title_lookup[lower]

    # 3. Fuzzy match (return None — caller decides how to handle)
    return None


def get_close_title_suggestions(raw_title: str, n: int = 5) -> list[str]:
    """Return up to *n* titles that are close to *raw_title*."""
    lower = raw_title.strip().lower()
    matches = get_close_matches(lower, model_loader.title_lookup.keys(), n=n, cutoff=0.5)
    return [model_loader.title_lookup[m] for m in matches]


def get_movie_info(title: str) -> dict | None:
    """Return metadata dict for a single movie, or None."""
    canonical = resolve_title(title)
    if canonical is None:
        return None

    idx = model_loader.indices[canonical]
    if hasattr(idx, '__len__'):
        idx = int(idx.iloc[0])
    else:
        idx = int(idx)

    row = model_loader.df.iloc[idx]
    return {
        "title": str(row.get("title", "")),
        "genres": str(row.get("genres", "")),
        "vote_average": float(row.get("vote_average", 0.0)),
        "overview": str(row.get("overview", "")),
        "tagline": str(row.get("tagline", "")),
        "popularity": float(row.get("popularity", 0.0)),
    }


def get_recommendations(title: str, n: int = 10) -> list[dict]:
    """Return *n* recommended movies for the given *title*.

    Each item in the returned list is a dict with keys:
        title, genres, vote_average, overview, tagline

    Raises:
        ValueError  — if the title cannot be resolved.
    """
    canonical = resolve_title(title)
    if canonical is None:
        suggestions = get_close_title_suggestions(title)
        msg = f"Movie '{title}' not found."
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        raise ValueError(msg)

    idx = model_loader.indices[canonical]

    # Handle duplicate titles — indices might return a Series instead of scalar
    if hasattr(idx, '__len__'):
        idx = int(idx.iloc[0])
    else:
        idx = int(idx)

    # Compute cosine similarity for this single movie against all others
    sim_scores = cosine_similarity(
        model_loader.tfidf_matrix[idx:idx+1], model_loader.tfidf_matrix
    ).flatten()

    # Get top-n indices (skip the movie itself at position 0)
    top_indices = sim_scores.argsort()[::-1]
    similar_indices = [i for i in top_indices if i != idx][:n]

    results: list[dict] = []
    for i in similar_indices:
        row = model_loader.df.iloc[i]
        results.append(
            {
                "title": str(row.get("title", "")),
                "genres": str(row.get("genres", "")),
                "vote_average": float(row.get("vote_average", 0.0)),
                "overview": str(row.get("overview", "")),
                "tagline": str(row.get("tagline", "")),
                "popularity": float(row.get("popularity", 0.0)),
            }
        )

    logger.info("Generated %d recommendations for '%s'", len(results), canonical)
    return results
