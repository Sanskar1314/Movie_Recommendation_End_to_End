# Project development memory

## 2026-10-23 — Inspection and initial plan
Inspected all tracked runtime modules, notebook cells, local data/artifacts, dependency files, launcher and Git status before changes. Stack: Python 3.12 environment, FastAPI 0.111, Streamlit 1.36, pandas 2.2, NumPy 2, SciPy 1.13, scikit-learn 1.5. Dataset: 45,447 processed metadata rows, no ratings. Notebook uses TF-IDF text cosine and drops IDs; directory spelling differs from its CSV path. No tests, database or documentation existed.

Pre-existing user changes: deleted root app.py/main.py, modified frontend/app.py, untracked run.sh. Preserve those changes. .env exists and must remain private. Avoid reading or printing credentials.

Plan: preserve legacy content discovery; add real MovieLens-small explicit ratings, user-based neighborhood CF, SQLite local profiles and ratings, native Streamlit controls, official download script and reproducible evaluation. Small user count makes on-demand sparse neighbor scoring understandable and practical; item similarity would require more storage, factorization adds training/artifact complexity. Initial docs created before application implementation. All implementation and evaluation still pending.

## 2026-10-23 — Data and recommendation engine
Downloaded the official GroupLens MovieLens latest-small archive; preserved its license README and source SHA256 locally. It has 100,836 valid ratings from 610 users across a 9,742-movie catalog. Downloaded data and local SQLite files are Git-ignored. No fabricated production interactions. Optional posters join links.csv TMDB IDs to original metadata IDs; title matching is not used.

Implemented sparse user-based CF using Pearson correlation over co-rated movies, at least three shared ratings, overlap/(overlap+10) shrinkage, at most 40 positive neighbors, and at least two neighbor ratings for each predicted movie. Predictions use target mean plus weighted neighbor deviations; missing observations remain unknown. Unsupported candidates use a Bayesian rating baseline with 10 global-mean prior observations and explicit source labels. Rated and evidence-free movies are excluded. No serialized CF artifact; reconstruct from CSV plus SQLite snapshot per inference.

## 2026-10-23 — Persistence and integration
Added local nickname profiles and SQLite half-star rating upserts with timestamps, foreign keys and transaction handling. Local IDs are offset above MovieLens user IDs internally. Added /personal APIs and For You UI with profile creation/switching, rating search/edit, saved history, refresh and explicit fallback states. Preserved legacy browse/detail and TF-IDF. Fixed non-finite legacy numeric metadata and duplicate autocomplete titles, plus dark input contrast. Root requirements now includes both backend/frontend dependencies. Launcher binds locally and manages both processes.

## 2026-10-23 — First evaluation
Executed deterministic seed-42 per-user 20% random holdout: 80,896 train / 19,940 test ratings. All means, neighbors and popularity statistics are fit on train only. CF-with-fallback RMSE 0.926745 vs baseline 0.959934; MAE 0.711391 vs 0.747668. Top-10 Precision 0.026711 vs 0.087312, Recall 0.015694 vs 0.067683, NDCG 0.035163 vs 0.105457 (599 users with relevant holdouts). CF covers 70.64% of held-out predictions. This engine improves rating error but underperforms popularity on ranking; no claim of superior top-N quality. Results in reports/evaluation.json. Nine initial unit/API tests passed; UI and live startup checks are in progress.

## 2026-10-23 — UI verification and refinement
Streamlit AppTest executed the actual frontend against the FastAPI TestClient with real MovieLens CSVs and a temporary SQLite database: create profile, save rating, refresh, create another profile, switch back, legacy browse and Toy Story detail. The test adapter needed requests-compatible response metadata. A later stale-ID cleanup exposed an empty SQLite-frame dtype error; fixed numeric conversion and added an empty-validation regression assertion. Optional TMDB calls were disabled in tests.

Live run.sh verification passed on spare ports 18001/18501: FastAPI healthy with both services ready, Streamlit health 200, MovieLens search 200, and existing Toy Story recommendations Toy Story 2 / Toy Story 3 / Small Fry. Default port 8501 was occupied; no existing service was stopped. Temporary smoke services shut down. Launcher now accepts BACKEND_PORT/FRONTEND_PORT and sets the frontend URL. The initial sandbox denied socket operations; approved local smoke execution succeeded. No approval rejection left work blocked.

Fixed the original notebook's Dataset/Datset path mismatch (notebook training itself was not rerun). Introduced a specific UnknownProfileError so unrelated KeyError defects are not silently converted into profile errors. Limited browser CORS origins to local Streamlit defaults. Legacy metadata numbers are normalized for valid JSON; all_titles now has 42,277 case-sensitive unique titles (45,447 metadata rows), while lowercase lookup has 42,227 entries. No useful legacy files were removed. Pre-existing deleted root files remain untouched.

## Handoff: limitations and next work
- CF improves held-out rating error but has substantially worse top-N ranking than popularity; confidence-aware ranking and validation on additional/temporal splits are future work.
- Profiles are shared local data without authentication; launch defaults to loopback. Do not expose the API as a production user service.
- No unified rating action on legacy detail pages: rate the corresponding ID-safe MovieLens entry in For You.
- Historical MovieLens development dataset, one fixed random split, no production or temporal quality claim. Fallback contributes to reported rating metrics.
- Full model rebuild per request is suitable for this small dataset; large deployments need measured caching/training strategies.
- CSV changes need restart; SQLite rating changes are immediate. Stale IDs are excluded from inference and labeled unavailable in history.
- Legacy pickles/raw metadata are available locally but ignored by Git. New checkouts need the download script for personal recommendations and trusted original artifacts for legacy browsing. Optional notebook libraries are not runtime dependencies.
- Optional TMDB API calls, browser pixel-level layout and full mobile/accessibility behavior were not verified. No new runtime library was introduced.
- Added: six mandatory documents, README, collaborative engine, store, personal routes, download/evaluation CLIs, tests and executed report. Modified: API startup/health/errors, loader metadata cleanup, health schema, frontend integration, requirements, launcher, ignore rules and notebook path.

## 2026-10-23 — Final verification
All ten tests passed with no skips in the provided workspace, including the real-data UI journey and legacy assertions. Re-ran real-data evaluation after final validation changes; recorded metrics are unchanged. Added signed-64-bit API ID bounds to reject oversized identifiers before SQLite binding. Python compilation, bash syntax, git diff whitespace checks and pip dependency consistency passed. Live startup on spare ports passed as recorded above. All six mandatory documents, README, task checklist and executed report are complete. No blocking implementation tasks remain in this scope; quality, authentication and accessibility enhancements remain explicitly future work. No commits were made.

## 2026-10-23 — Connection-refused follow-up
User reported frontend connection refusal to port 18001. Inspection found both processes running and successful profile/recommendation requests, so the failure was transient; its exact timing was not reproduced. Updated run.sh to wait up to 30 seconds for backend HTTP readiness before starting Streamlit. Added concise connection/timeout messages and Retry connection while retaining diagnostic logging. Added a Streamlit regression test that simulates connection refusal then successful retry; both UI tests passed. Existing active services remain on 18001/18501.

## 2026-10-23 — Poster recovery
Diagnosed three sources of missing posters: 201 catalog entries lack local paths, some historical paths now return HTTP 404, and .env contains only BACKEND_URL (no TMDB key). User explicitly authorized using the existing TMDB key, but none was configured at verification time. Automatic review initially blocked key transmission; user approval resolved that permission issue, while configuration remains missing.

Added frontend/posters.py to share local metadata reuse across both views, validate fetched image responses, embed successful image bytes, and recover missing/stale paths using exact TMDB IDs. Unknown legacy titles require matching title/year in search results. Added tmdb_id to personal metadata responses. Image/API requests have timeouts, sanitized logs and five-minute caches; key configuration is read anew so adding .env credentials does not require restart. Grid requests use eight workers. No new dependency. Sixteen tests passed, including five poster tests; authenticated lookup tested with mocks because no live key exists. Real downloads confirmed Jumanji and The Godfather posters load, while sampled old Toy Story, Shawshank and Fight Club paths are unavailable. No claim that every movie now has a real poster.

## 2026-10-23 — TMDB credential verified
User saved TMDB_API_KEY in the ignored .env file. Verified v3 key format without printing it, authenticated movie-details HTTP 200, and successful end-to-end Toy Story/Fight Club poster recovery. Initial connection failures were transient; subsequent requests succeeded. Both local service health checks returned 200. F4 is complete. The credential was sent only to TMDB under the user's explicit authorization and was not included in logs or documentation.

## 2026-10-23 — GitHub synchronization authorization
User requested that appropriate completed changes be committed and pushed to GitHub. Saved this preference in rules.md. Remote main contained a newer README-only commit, so preserve that commit and incorporate its legacy artifact-generation guidance (with the corrected dataset path) into the current README before publishing the upgrade. Secret scan confirmed the configured TMDB key is absent from commit candidates; .env, source datasets, local ratings and pickles remain ignored.
