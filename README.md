# MovieMind

A personalized movie recommender using **user-based collaborative filtering**, alongside the existing TF-IDF movie discovery experience. FastAPI, Streamlit, pandas/SciPy and standard-library SQLite; no new runtime dependency or paid API is required.

## Run locally

Use Python 3.12 (the version verified here), from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_movielens.py
./run.sh
```

The launcher waits for backend readiness before starting Streamlit. If the backend becomes temporarily unreachable, For You offers a Retry connection button.

Open [MovieMind](http://localhost:8501) and [API documentation](http://localhost:8000/docs). Create a nickname in **For You**, search movies and save ratings. Rate at least three movies with varied scores, preferably more, to find shared evidence. Ratings persist in `data/preferences.sqlite3`. Switch profiles to compare preferences. Community fallback is shown whenever evidence is insufficient. **Browse Movies** retains legacy search and detail recommendations.

If ports are occupied:

```bash
BACKEND_PORT=18001 FRONTEND_PORT=18501 ./run.sh
```

To run services separately:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# In a second terminal, with the same virtual environment active:
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Optional environment settings: `MOVIELENS_DIR` (CSV directory), `RATINGS_DB` (writable SQLite path), `PICKLE_DIR` (trusted legacy artifacts), `BACKEND_URL` (frontend API base URL), `TMDB_API_KEY` (recover missing/stale posters in both views). Existing `.env` settings are respected; environment variables take precedence. To use alternate ports with a preconfigured `BACKEND_URL`, update that URL too. Both views reuse existing raw metadata without an API key. Posters are downloaded and checked server-side, then displayed inline. Missing/stale URLs fall back to TMDB details by movie ID when TMDB_API_KEY is configured; unavailable images show a placeholder. Poster successes and failures are cached for five minutes, and the key is re-read from .env on requests.

## Data and existing artifacts

The setup script downloads genuine [MovieLens latest-small](https://grouplens.org/datasets/movielens/latest/) from GroupLens and preserves its README/license. It is a research/development dataset with commercial-use restrictions; read `data/ml-latest-small/README.txt` before reuse. Acknowledge Harper and Konstan (2015), *The MovieLens Datasets: History and Context*, DOI [10.1145/2827872](https://doi.org/10.1145/2827872). Source URL and archive SHA256 are saved locally. Data is not committed.

The current workspace also contains the original `Datset/movies_metadata.csv` and four trusted pickles in `pickle_files/`: `df.pkl`, `indices.pkl`, `tfidf.pkl`, `tfidf_matrix.pkl`. These remain Git-ignored. A fresh checkout can run **For You** after downloading MovieLens; legacy browsing requires restoring these artifacts. The original notebook documents their generation (optional notebook dependencies include nltk, matplotlib and seaborn). Never unpickle untrusted downloads. Optional poster enrichment maps MovieLens IDs through `links.csv` to raw metadata TMDB IDs; it does not join by title.

## Optional legacy artifact generation

To regenerate the original TF-IDF artifacts, place the source CSV at `Datset/movies_metadata.csv` in the repository root. Install notebook-only dependencies and open the notebook:

```bash
python -m pip install jupyterlab nltk matplotlib seaborn
jupyter lab
```

Run `notebook/movies.ipynb` with the kernel working directory set to either the root or `notebook/`; its corrected path handles both. NLTK downloads stopwords and WordNet. If running from `notebook/`, move its four generated artifacts from the repository root with:

```bash
mkdir -p pickle_files
mv notebook/df.pkl notebook/indices.pkl notebook/tfidf.pkl notebook/tfidf_matrix.pkl pickle_files/
```

On Windows, activate the environment with `.venv\Scripts\activate`. The existing title-similarity API remains available:

```bash
curl -X POST http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"movie":"Toy Story","n":5}'
```

## Algorithm in plain language

Compare the movies you and another viewer both rated. A viewer whose ratings rise and fall like yours becomes a neighbor. Use up to 40 positively correlated neighbors, downweight weak overlaps, and estimate your unseen ratings from their preferences relative to their usual rating level. Your ratings set your own usual level. At least three shared ratings and two neighbors supporting a candidate are required. Missing ratings are unknown. Already-rated movies are excluded.

Where neighbors cannot support a prediction, use a community mean with ten global-average prior ratings and label it **popularity**. A low-count movie therefore cannot lead the fallback list on one perfect rating alone. New movies stay searchable but are not recommended until they have ratings. A local preference edit takes effect on the next request; the small sparse interaction model is rebuilt from source CSVs plus a database snapshot.

## Tests and evaluation

```bash
python -m unittest discover -s tests -v
python scripts/evaluate.py
python -m pip check
```

The sixteen-test suite covers hand-calculated CF behavior, cold/sparse users, unknown IDs, validation, deduplication, exclusion, empty output, deterministic splitting, SQLite persistence, API errors and real-data Streamlit journeys. Its UI integration test is skipped when MovieLens has not been downloaded. Legacy UI assertions run when trusted pickles are available. Fixture ratings test arithmetic only; production training and evaluation use real MovieLens interactions.

Actual seed-42 random per-user holdout: **80,896 train / 19,940 test** ratings; ranking averages over 599 users with a held-out rating ≥4. All inference statistics use training observations only. Candidate set: full unseen catalog with training rating evidence. Baseline: the same Bayesian community ranking, excluding seen titles.

| Metric | CF with labeled fallback | Popularity |
|---|---:|---:|
| RMSE ↓ | 0.926745 | 0.959934 |
| MAE ↓ | 0.711391 | 0.747668 |
| Precision@10 ↑ | 0.026711 | 0.087312 |
| Recall@10 ↑ | 0.015694 | 0.067683 |
| NDCG@10 ↑ | 0.035163 | 0.105457 |

CF supported 70.64% of held-out predictions. **Rating error improved, but top-N ranking underperformed popularity.** This is a transparent internship implementation, not a claim of superior recommendation quality. See [the executable report](reports/evaluation.json). This development dataset and single random split do not establish future, causal or production performance. Missing held-out relevance is not proof of dislike.

## Scope and limitations

Profiles have no authentication and are intended for a trusted local demonstration; anyone with API access can select them. Keep the launcher bound to localhost. The legacy and MovieLens catalogs intentionally remain separate because the processed catalog lost IDs; a legacy movie click does not submit a personal rating. Search the MovieLens catalog to rate it. The default MovieLens catalog is historical (2018), and only observed-rating evidence is modeled. No implicit watched history is collected. Dataset files load at startup; restart after replacing them. Local ratings are read on every recommendation request. Full model rebuilds are appropriate for this small dataset, not large production workloads. Native controls work at narrow widths, but legacy six-column grids and muted text need a dedicated responsive/accessibility pass. Pixel-level browser review was not performed. Public image downloads and authenticated TMDB recovery were verified with Toy Story and Fight Club.

See [PRD.md](PRD.md), [architecture.md](architecture.md), [rules.md](rules.md), [design.md](design.md), [tasks.md](tasks.md) and [memory.md](memory.md) for requirements, design decisions and handoff context.
