# Implementation task tracker

Status values: Pending / In Progress / Completed / Blocked.

## Analysis

- [x] **A1** Inspect structure, code, datasets and gaps — **Completed**. Files: `existing code and notebook`. Acceptance: Inspection documented.

## Data preparation

- [x] **D1** Verify license and download real MovieLens data — **Completed**. Files: `scripts/download_movielens.py`. Acceptance: Official README retained, schema validated.
- [x] **D2** Validate and map interactions — **Completed**. Files: `backend/collaborative.py`. Acceptance: Invalid rows rejected, duplicates resolved, IDs stable.

## Recommendation engine

- [x] **R1** Implement sparse CF scoring and cold-start — **Completed**. Files: `backend/collaborative.py`. Acceptance: Rank unseen movies using real multi-user ratings and labeled fallback.

## Application integration

- [x] **I1** Persist local profiles and ratings — **Completed**. Files: `backend/store.py`. Acceptance: Ratings survive restart and updates.
- [x] **I2** Add validated API and integrate UI — **Completed**. Files: `backend/routes/personal.py, frontend/app.py`. Acceptance: Profiles, rating form and fresh personal results work.

## Testing and evaluation

- [x] **T1** Test engine, persistence and API — **Completed**. Files: `tests/`. Acceptance: Executed tests pass.
- [x] **T2** Evaluate real held-out data against baseline — **Completed**. Files: `scripts/evaluate.py, reports/`. Acceptance: Leakage-free real metrics saved.
- [x] **T3** Verify application startup and existing features — **Completed**. Files: `backend/main.py, frontend/app.py`. Acceptance: Health, legacy recommendations and UI smoke checks pass.

## Documentation and cleanup

- [x] **F1** Complete docs, instructions and final audit — **Completed**. Files: `six root documents, README.md, requirements.txt`. Acceptance: Docs match executed implementation and known limits.

## Connection recovery follow-up

- [x] **F2** Handle transient backend connection failure — **Completed**. Files: `run.sh`, `frontend/app.py`, `tests/test_ui.py`. Acceptance: backend readiness gate, clear connection error, successful retry regression and existing UI journey pass.

## Poster recovery follow-up

- [x] **F3** Reuse and validate posters in both views — **Completed**. Files: `frontend/posters.py`, `frontend/app.py`, personal metadata, tests and docs. Acceptance: local reuse, ID-safe recovery, clean failures and sixteen tests pass.
- [x] **F4** Verify authenticated recovery against TMDB — **Completed**. Files: private `.env`. Acceptance: user configures TMDB_API_KEY; confirm a previously missing poster loads. Configured key validated with HTTP 200; Toy Story and Fight Club posters loaded successfully.
