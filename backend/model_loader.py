"""
Model Loader — Loads all pickle artifacts once at startup.

This module provides a singleton-style loader that reads the pre-trained
TF-IDF vectorizer, TF-IDF matrix, movie DataFrame, and title-to-index
mapping from disk exactly once. All other modules import from here.
"""

import os
import pickle
import logging

import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# ── Module-level state (loaded once) ────────────────────────────────
df: pd.DataFrame = None
indices: pd.Series = None
tfidf: TfidfVectorizer = None
tfidf_matrix: csr_matrix = None

# Case-insensitive lookup: lowercase title → original title
title_lookup: dict[str, str] = {}

# Sorted list of all movie titles (for frontend autocomplete)
all_titles: list[str] = []

_loaded: bool = False


def load_artifacts(pickle_dir: str | None = None) -> None:
    """Load all pickle files from the given directory.

    Args:
        pickle_dir: Path to the directory containing .pkl files.
                    Defaults to ``../pickle_files`` relative to this file.
    """
    global df, indices, tfidf, tfidf_matrix, title_lookup, all_titles, _loaded

    if _loaded:
        logger.info("Artifacts already loaded — skipping.")
        return

    if pickle_dir is None:
        pickle_dir = os.path.join(os.path.dirname(__file__), "..", "pickle_files")

    pickle_dir = os.path.abspath(pickle_dir)
    logger.info("Loading model artifacts from: %s", pickle_dir)

    # ── Load each artifact ──────────────────────────────────────────
    with open(os.path.join(pickle_dir, "df.pkl"), "rb") as f:
        df = pickle.load(f)
    logger.info("  ✓ df.pkl loaded — shape %s", df.shape)

    with open(os.path.join(pickle_dir, "indices.pkl"), "rb") as f:
        indices = pickle.load(f)
    logger.info("  ✓ indices.pkl loaded — %d entries", len(indices))

    with open(os.path.join(pickle_dir, "tfidf.pkl"), "rb") as f:
        tfidf = pickle.load(f)
    logger.info("  ✓ tfidf.pkl loaded")

    with open(os.path.join(pickle_dir, "tfidf_matrix.pkl"), "rb") as f:
        tfidf_matrix = pickle.load(f)
    logger.info("  ✓ tfidf_matrix.pkl loaded — shape %s", tfidf_matrix.shape)

    for column in ('vote_average', 'popularity'):
        df[column] = pd.to_numeric(df[column], errors='coerce').replace([float('inf'), -float('inf')], 0).fillna(0)
    for column in ('title', 'overview', 'genres', 'tagline'):
        df[column] = df[column].fillna('').astype(str)

    # ── Build case-insensitive lookup ───────────────────────────────
    title_lookup = {title.lower(): title for title in indices.index}
    all_titles = sorted(set(indices.index.tolist()))
    logger.info("  ✓ Title lookup built — %d unique titles", len(title_lookup))

    _loaded = True
    logger.info("All artifacts loaded successfully.")
