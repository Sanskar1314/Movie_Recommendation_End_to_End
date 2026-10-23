# UI/UX design system

The existing Streamlit UI is implemented and is preserved. MovieMind uses a dark cinema theme, browse grid, detail hero, horizontal genre rows and native widgets. Fonts: Inter for body and Space Grotesk for headings, with sans-serif fallback. Primary red #E50914; page #0A0A0F; cards #181818; gradients #1A1A2E, #16213E, #0F3460; text #E5E5E5 and #FFFFFF; muted white with opacity. Cards use 8px radius, inputs 10px, hero 20px; spacing roughly 4/8/12/16/24/32/40px. Logo 3.2rem, hero 2.4rem, section 1.3rem, body .95rem, card .8rem.

Use existing red buttons and dark cards. The For You view adds a native profile selector, rating form (0.5–5), personal recommendation list and explicit score/source labels. Keep personal recommendations separate from the legacy More Like This section. Genres are presentation metadata, never the CF signal. Optional posters must have placeholders without requiring credentials.

Show spinner during inference, onboarding for no ratings, an empty message for exhausted candidates and actionable errors for unavailable data/API. Retain title search and URL browse/detail navigation. Hover enlarges cards and red highlights focus. Use labeled widgets and keyboard navigation. Respect narrow screens with wrapping controls; current six-column legacy grids remain a known small-screen limitation. Dark input text contrast is fixed to #E5E5E5. Do not hide native controls required for navigation. The controls are implemented and exercised with Streamlit AppTest. Pixel-level browser inspection and a full accessibility review were not performed.


## Implemented components

The primary navigation is a native horizontal radio (For You / Browse Movies); existing detail URLs and Back to Browse link remain. For You uses expandable profile creation, a nickname field (60 characters), profile selectbox with numeric suffix to distinguish duplicate names, MovieLens search and ID-safe movie selectbox. A labeled native slider offers 0.5–5 stars in half-star steps. Create profile and Save rating are form actions; Refresh recommendations triggers a fresh run. Saved history is a native dataframe. Duplicate nicknames are allowed because profile IDs distinguish them.

Personal recommendation rows use 1:5 poster/detail columns, 90px optional poster or film placeholder, bold title, muted genres, score and source, observed rating count and MovieLens ID. Scores use a five-star scale; legacy metadata ratings use its original ten-point scale. Personal results do not link to legacy titles because catalog identity is not established. Blank poster URLs never require a credential. TMDB-hosted images require network connectivity. The server verifies them and embeds working images inline; unavailable personal images show “Poster unavailable”. Both views use local data first and optional TMDB recovery.

## States and interaction details

- Loading: spinner while comparing ratings; forms disable submission until their normal Streamlit rerun completes.
- No profile: expanded creation form and instruction to create a nickname.
- No history: saved-history information and community-pick explanation.
- Search empty: clear message; rating submit is absent.
- Fallback/mixed: info banners explain the source and each result carries its own source label.
- No candidates: no-unseen-movies information.
- API/storage/data errors: native error message with actionable API detail; connection failures and timeouts use concise messages and a Retry connection button. Diagnostic details remain in server logs. Legacy error cards remain.
- Hover: original cards enlarge to 1.05 with shadow; back link gains a red background tint. Native controls retain keyboard focus and selected state.

## Responsive and accessibility limits

Native text inputs, forms and dataframes use Streamlit's responsive container behavior; the personal list wraps text. Legacy browse grids remain six columns and hero posters have a fixed width. Muted text in the original theme can have low contrast. Font imports can fail offline, so sans-serif fallbacks remain. Semantic native controls carry visible labels; HTML images have title alt text in legacy views, while personal st.image uses the adjacent title. A full screen-reader, touch, zoom and contrast audit remains future work. Do not claim WCAG compliance from the widget smoke tests.
