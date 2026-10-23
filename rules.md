# Development rules

Read PRD.md, architecture.md, tasks.md and memory.md before editing. Check current code and user changes; update these documents after meaningful phases and never mark work complete without executed evidence.

Use idiomatic Python, existing naming, meaningful names, focused functions and straightforward control flow. Avoid duplicate logic, unnecessary patterns, trivial wrappers and comments that repeat code. Preserve unrelated modules and useful functionality. Reuse pandas, NumPy, SciPy, FastAPI and Streamlit; SQLite is standard library. Add dependencies only for a demonstrated need. Do not add secrets, paid API requirements or unrelated features.

Separate HTTP, persistence, dataset loading and scoring. Never fabricate ratings or metrics. Keep MovieLens IDs separate from TMDB IDs and legacy title indices. Missing ratings are unknown. Split before fitting every statistic, including popularity and user means. Fix seeds and retain evaluation configuration. Unknown users/movies, sparse histories and cold-start must be explicit. Do not call fallback collaborative filtering.

Missing CSVs and legacy pickles must produce actionable setup instructions. Validate API inputs and rating range. Surface database failures without exposing private paths or profiles. Handle empty results and missing optional metadata. Log operational failures; do not silently hide exceptions. Only load trusted local pickle files.

Do not rewrite unrelated code or change stacks without justification. Keep docs accurate, record limitations and tests actually run, and never claim an unverified feature works. Generated tests may use small hand-calculated fixtures, clearly separated from real training and evaluation data.

## GitHub synchronization preference
The user authorized committing and pushing appropriate completed changes to GitHub. After a coherent change is implemented and relevant checks pass, inspect the diff, preserve concurrent remote work, commit and push to the appropriate repository branch. Do not include credentials, local ratings, downloaded datasets or model artifacts. Never force-push or overwrite unrelated work to resolve a rejected push. Report the commit and any blocked push honestly.
