# Product requirements — MovieMind

## Overview and problem

MovieMind helps viewers discover movies through personal ratings and recommendations. The original FastAPI/Streamlit application compares a selected movie's text features against 45,447 metadata records. It provides search, popularity browsing, posters, a detail hero and genre-grouped TF-IDF recommendations. Every viewer selecting the same title receives the same suggestions. It has no user history, persistent feedback or personalized evaluation.

The upgrade serves viewers who want suggestions reflecting their own preferences and internship reviewers who need an understandable, reproducible implementation. Genuine multi-user MovieLens ratings power collaborative filtering. The existing discovery experience remains available.

## Objectives and scope

- Create individual local profiles and persist explicit movie ratings.
- Learn from relationships between users' movie ratings, rather than matching genre labels.
- Rank unseen movies, show metadata, and distinguish collaborative scores from fallback.
- Make preference edits visible on the next recommendation request.
- Demonstrate correctness with tests and real-data evaluation against popularity.
- Preserve Python, FastAPI, Streamlit and the working legacy flow.

Implemented scope: trusted local demonstration using MovieLens latest-small and SQLite. The system does not collect watch events or likes; all ratings are explicit half-stars. No authentication, payments, administrative dashboard or new infrastructure is included. Personal and legacy catalogs remain separate: the processed legacy dataset lacks stable IDs. The UI clearly searches the MovieLens catalog when collecting ratings.

## Functional requirements and delivered features

| ID | Requirement | Delivered behavior |
|---|---|---|
| FR1 | Profiles | Create nicknames and switch profiles; shared local profiles need no account |
| FR2 | Ratings | Search by title, rate 0.5–5 in 0.5 steps, edit existing ratings |
| FR3 | Persistence | SQLite upsert stores one rating per user/movie with timestamp across restarts |
| FR4 | Personalization | Up to 40 positive Pearson neighbors supply rating-deviation predictions |
| FR5 | Exclusion/ranking | Exclude rated movies, rank by estimated rating, deterministic tie-breaking |
| FR6 | Metadata | MovieLens ID, title, genres, score, evidence count and optional poster |
| FR7 | Cold-start | Explicit popularity fallback and onboarding guidance; no false CF claims |
| FR8 | Validation | Unknown local profile/movie 404, invalid input 422, unavailable service 503 |
| FR9 | Existing features | Legacy browse, search, popular list, detail and More Like This retained |
| FR10 | Evaluation | Reproducible held-out metrics, popularity comparison and checked-in report |

## Recommendation behavior

A user needs varied ratings and at least three co-rated movies with another viewer to establish Pearson evidence. Similarity is shrunk for limited overlap. A prediction needs at least two supporting neighbors. User and neighbor rating levels are accounted for with observed-history means. Unsupported candidates use a Bayesian community rating; each movie shows its source and the response reports collaborative/popularity/mixed/empty. Source ratings are real MovieLens observations; local feedback augments them. Genres and text never influence CF scoring.

New users see community picks and a prompt to rate movies. Sparse or constant histories fall back safely. New movies remain searchable; with no rating evidence they are excluded from ranked suggestions. If every eligible movie is rated, show an empty state. Rating edits rerun scoring from a fresh database snapshot. Replacing CSVs requires server restart.

## User journeys

1. A new viewer opens For You, creates a nickname and sees labeled community picks. They search and rate several movies, then receive supported personal predictions where overlap permits.
2. Two viewers with different rating patterns select their own profiles and receive different ranked suggestions. Differences depend on real interaction evidence, not predetermined genre personas.
3. A viewer changes a saved rating; the app upserts it, reruns and displays refreshed scores. Their saved history remains after restart.
4. A viewer chooses Browse Movies, searches Toy Story and opens its original detail page. More Like This remains title-based content discovery. To personalize, they return to For You and rate the MovieLens record.
5. Missing source data produces a setup error explaining how to download MovieLens; other available subsystems can still operate.

## Non-functional requirements

Keep the implementation readable, reproducible, CPU-friendly at 610 source users and 100,836 ratings, and independent of paid APIs. Preserve stable identifier mapping and treat unknown preferences as missing. Keep private interactions and credentials out of Git. Bind local services to loopback by default. Use timeouts and actionable UI errors. Native controls are labeled and keyboard-accessible; a complete accessibility audit has not been performed. Rebuild the sparse model on demand at this dataset size rather than introduce a training scheduler or stale model artifact.

## Success criteria and measured outcome

Delivered correctness checks cover distinct user preferences, genuine multi-user signals, exclusion, sparse/unknown users, invalid movie IDs, ranked scores, persistence and refresh, API errors and Streamlit integration. All tests must be executed successfully before completion. The six root documents must match the implementation. Application startup must be verified and existing discovery must still work.

The executed holdout evaluation improves RMSE from 0.959934 to 0.926745 but underperforms popularity in top-N ranking (Precision@10 0.026711 vs 0.087312). Personalization works; better ranking quality remains an enhancement objective, not an achieved claim. Full metrics/configuration are in README.md and reports/evaluation.json.

## Future enhancements

Improve top-N quality with confidence-aware scoring validated on separate splits; perform temporal evaluation; add authentication before multi-user deployment; unify catalogs only through reliable original identifiers; improve legacy mobile grids and accessibility; cache models by interaction version if workload grows. No such future capability is presented as implemented.
