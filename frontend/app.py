"""
MovieMind — AI-Powered Movie Recommendations (Netflix-style).

Two-page Streamlit app:
  - Homepage: browsable grid of clickable movie posters
  - Detail page: hero banner + genre-grouped recommendation rows
"""

import os
import logging
import html as html_lib
import urllib.parse
import requests
import streamlit as st
from dotenv import load_dotenv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from frontend.posters import poster_source

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="MovieMind — AI Movie Recommendations",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');

.stApp { background:#0a0a0f; font-family:'Inter',sans-serif; color:#e5e5e5; }
#MainMenu,footer,header { visibility:hidden; }
.stDeployButton,div[data-testid="stToolbar"],div[data-testid="stDecoration"] { display:none; }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(229,9,20,0.4); border-radius:3px; }

/* Header */
.mm-header { text-align:center; padding:2rem 1rem 0.5rem; }
.mm-logo { font-family:'Space Grotesk',sans-serif; font-size:3.2rem; font-weight:800; color:#e50914; letter-spacing:-1px; margin-bottom:0.1rem; }
.mm-tagline { font-size:0.85rem; color:rgba(255,255,255,0.3); font-weight:300; letter-spacing:2px; text-transform:uppercase; }

/* Search */
div[data-baseweb="input"] input, .stTextInput input {
    background:rgba(255,255,255,0.06) !important; border:1px solid rgba(255,255,255,0.1) !important;
    border-radius:10px !important; color:#e5e5e5 !important; font-size:1rem !important; padding:0.6rem 1rem !important;
}
div[data-baseweb="input"] input:focus, .stTextInput input:focus {
    border-color:rgba(229,9,20,0.5) !important; box-shadow:0 0 16px rgba(229,9,20,0.1) !important;
}

/* Back button */
.back-btn { display:inline-flex; align-items:center; gap:0.4rem; background:rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.5rem 1.2rem;
    color:rgba(255,255,255,0.7); font-size:0.9rem; cursor:pointer; transition:all 0.2s; text-decoration:none; margin-bottom:1rem; }
.back-btn:hover { background:rgba(229,9,20,0.15); border-color:rgba(229,9,20,0.3); color:#fff; }

/* Movie grid card — wrapped in <a> link */
.mgrid-link { text-decoration:none; color:inherit; display:block; }
.mgrid-card { background:#181818; border-radius:8px; overflow:hidden; transition:all 0.3s cubic-bezier(0.4,0,0.2,1); cursor:pointer; }
.mgrid-card:hover { transform:scale(1.05); box-shadow:0 12px 40px rgba(0,0,0,0.7); z-index:10; position:relative; }
.mgrid-poster { width:100%; aspect-ratio:2/3; overflow:hidden; background:linear-gradient(135deg,#1e1e2e,#252540); display:flex; align-items:center; justify-content:center; }
.mgrid-poster img { width:100%; height:100%; object-fit:cover; display:block; }
.mgrid-poster-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:2.8rem; opacity:0.2; aspect-ratio:2/3; }
.mgrid-title { padding:0.6rem 0.5rem; font-weight:600; font-size:0.8rem; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* Hero banner */
.hero-banner { position:relative; background:linear-gradient(135deg,#1a1a2e 0%,#16213e 40%,#0f3460 100%);
    border-radius:20px; overflow:hidden; margin:1rem 0 2rem; min-height:320px; display:flex; align-items:center; }
.hero-backdrop { position:absolute; inset:0; background:radial-gradient(ellipse at 70% 50%,rgba(229,9,20,0.08),transparent 70%); }
.hero-content { position:relative; z-index:1; display:flex; gap:2.5rem; padding:2.5rem; width:100%; align-items:flex-start; }
.hero-poster { flex-shrink:0; width:200px; border-radius:12px; overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,0.5); }
.hero-poster img { width:100%; display:block; }
.hero-poster-placeholder { width:200px; height:300px; background:linear-gradient(135deg,#2a2a3e,#1a1a2e);
    display:flex; align-items:center; justify-content:center; font-size:4rem; opacity:0.3; border-radius:12px; }
.hero-info { flex:1; min-width:0; }
.hero-title { font-family:'Space Grotesk',sans-serif; font-size:2.4rem; font-weight:800; color:#fff; margin-bottom:0.5rem; line-height:1.15; }
.hero-meta { display:flex; align-items:center; gap:1rem; margin-bottom:1rem; flex-wrap:wrap; }
.hero-rating { background:rgba(229,9,20,0.15); color:#e50914; padding:0.3rem 0.8rem; border-radius:6px; font-weight:700; font-size:0.9rem; }
.hero-genre-tag { background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.7); padding:0.25rem 0.7rem; border-radius:4px; font-size:0.78rem; font-weight:500; }
.hero-tagline { font-style:italic; color:rgba(255,255,255,0.4); font-size:1rem; margin-bottom:1rem; }
.hero-overview { color:rgba(255,255,255,0.65); font-size:0.95rem; line-height:1.7; max-width:700px; }

/* Genre row */
.genre-row-title { font-family:'Space Grotesk',sans-serif; font-size:1.3rem; font-weight:700; color:#fff; margin:1.8rem 0 0.8rem; padding-left:0.25rem; }
.scroll-row { display:flex; gap:0.9rem; overflow-x:auto; padding-bottom:1rem; scroll-behavior:smooth; scrollbar-width:thin; }
.scroll-row::-webkit-scrollbar { height:4px; }
.scroll-row::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.15); border-radius:2px; }

/* Rec card */
.rec-card { flex:0 0 185px; background:#181818; border-radius:8px; overflow:hidden;
    transition:all 0.3s cubic-bezier(0.4,0,0.2,1); cursor:pointer; position:relative; }
.rec-card:hover { transform:scale(1.08); z-index:10; box-shadow:0 12px 40px rgba(0,0,0,0.7); }
.rec-poster { width:185px; height:278px; overflow:hidden; position:relative; background:linear-gradient(135deg,#1e1e2e,#252540); }
.rec-poster img { width:100%; height:100%; object-fit:cover; display:block; }
.rec-poster-ph { width:100%; height:100%; display:flex; align-items:center; justify-content:center; font-size:2.8rem; opacity:0.2; }
.rec-badge { position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.75); color:#fbbf24; padding:0.15rem 0.45rem; border-radius:4px; font-size:0.72rem; font-weight:700; }
.rec-body { padding:0.7rem 0.65rem; }
.rec-title { font-weight:600; font-size:0.82rem; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:0.3rem; }
.rec-genres { font-size:0.68rem; color:rgba(255,255,255,0.35); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* Error / prompt */
.err-card { background:rgba(229,9,20,0.08); border:1px solid rgba(229,9,20,0.2); border-radius:12px; padding:2rem; text-align:center; max-width:550px; margin:2rem auto; }
.err-card .err-icon { font-size:2.2rem; margin-bottom:0.5rem; }
.err-card .err-title { font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.1rem; color:#e50914; margin-bottom:0.4rem; }
.err-card .err-msg { color:rgba(255,255,255,0.45); font-size:0.9rem; }
.prompt-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:3.5rem 2rem; text-align:center; max-width:480px; margin:3rem auto; }
.prompt-card .p-icon { font-size:3rem; margin-bottom:1rem; opacity:0.4; }
.prompt-card .p-text { color:rgba(255,255,255,0.3); font-size:0.95rem; }

/* Footer */
.mm-footer { text-align:center; padding:3rem 1rem 2rem; color:rgba(255,255,255,0.12); font-size:0.78rem; }

/* Streamlit overrides */
div[data-testid="stHorizontalBlock"] { gap:0.75rem; }



</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════
def esc(text: str) -> str:
    if not text or str(text) == "nan":
        return ""
    return html_lib.escape(str(text))


def fetch_poster_url(title: str) -> str | None:
    return poster_source(title)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_movie_list() -> list[str]:
    try:
        resp = requests.get(f"{BACKEND_URL}/movies", timeout=10)
        resp.raise_for_status()
        return resp.json().get("titles", [])
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_popular_movies(n: int = 60) -> list[str]:
    """Fetch top movies by popularity for the homepage."""
    try:
        resp = requests.get(f"{BACKEND_URL}/movies/popular", params={"n": n}, timeout=10)
        resp.raise_for_status()
        return [m["title"] for m in resp.json().get("movies", [])]
    except Exception:
        return []


def navigate_to(page: str, movie_title: str = ""):
    st.session_state["page"] = page
    if movie_title:
        st.session_state["selected_movie"] = movie_title


def group_by_genre(recs: list[dict]) -> dict[str, list[dict]]:
    genre_map: dict[str, list[dict]] = defaultdict(list)
    for m in recs:
        raw = str(m.get("genres", ""))
        genres = [g.strip() for g in raw.split() if g.strip()]
        if genres:
            for g in genres[:2]:
                genre_map[g].append(m)
        else:
            genre_map["Other"].append(m)
    return dict(genre_map)


# ═══════════════════════════════════════════════════════════════════
#  Render: Header
# ═══════════════════════════════════════════════════════════════════
def render_header():
    st.markdown(
        '<div class="mm-header">'
        '<div class="mm-logo">MovieMind</div>'
        '<div class="mm-tagline">AI-powered movie recommendations</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════
#  Render: Hero Banner (detail page)
# ═══════════════════════════════════════════════════════════════════
def render_hero(movie: dict):
    title = esc(movie.get("title", ""))
    genres = str(movie.get("genres", ""))
    rating = movie.get("vote_average", 0)
    overview = esc(movie.get("overview", ""))
    tagline = esc(movie.get("tagline", ""))

    poster_url = fetch_poster_url(movie.get("title", ""))
    poster_html = (f'<div class="hero-poster"><img src="{poster_url}" alt="{title}"></div>'
                   if poster_url else '<div class="hero-poster-placeholder">🎬</div>')

    genre_list = [g.strip() for g in genres.split() if g.strip()]
    genre_tags = "".join(f'<span class="hero-genre-tag">{esc(g)}</span>' for g in genre_list)

    rating_val = f"{rating:.1f}" if rating > 0 else "N/A"
    rating_html = f'<span class="hero-rating">⭐ {rating_val}</span>'
    tagline_html = f'<div class="hero-tagline">"{tagline}"</div>' if tagline else ""
    overview_html = (f'<div class="hero-overview">{overview}</div>' if overview
                     else '<div class="hero-overview" style="opacity:0.3">No overview available.</div>')

    hero_html = (
        f'<div class="hero-banner">'
        f'<div class="hero-backdrop"></div>'
        f'<div class="hero-content">'
        f'{poster_html}'
        f'<div class="hero-info">'
        f'<div class="hero-title">{title}</div>'
        f'<div class="hero-meta">{rating_html}{genre_tags}</div>'
        f'{tagline_html}'
        f'{overview_html}'
        f'</div></div></div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  Render: Recommendation card (for genre rows)
# ═══════════════════════════════════════════════════════════════════
def build_card_html(movie: dict) -> str:
    title = esc(movie.get("title", "Unknown"))
    genres = str(movie.get("genres", ""))
    rating = movie.get("vote_average", 0)

    poster_url = fetch_poster_url(movie.get("title", ""))
    poster_inner = (f'<img src="{poster_url}" alt="{title}">'
                    if poster_url else '<div class="rec-poster-ph">🎬</div>')

    rating_val = f"{rating:.1f}" if rating > 0 else "N/A"
    star = "⭐" if rating >= 7 else "✦"
    genre_display = esc(" · ".join(g.strip() for g in genres.split() if g.strip()))

    return (
        f'<div class="rec-card">'
        f'<div class="rec-poster">'
        f'{poster_inner}'
        f'<div class="rec-badge">{star} {rating_val}</div>'
        f'</div>'
        f'<div class="rec-body">'
        f'<div class="rec-title">{title}</div>'
        f'<div class="rec-genres">{genre_display}</div>'
        f'</div></div>'
    )


def render_genre_row(genre_name: str, movies: list[dict]):
    cards_html = "".join(build_card_html(m) for m in movies)
    st.markdown(
        f'<div class="genre-row-title">{esc(genre_name)}</div>'
        f'<div class="scroll-row">{cards_html}</div>',
        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  PAGE: Homepage — Browse Movies
# ═══════════════════════════════════════════════════════════════════
def render_home():
    render_header()

    all_movies = fetch_movie_list()
    if not all_movies:
        st.markdown(
            '<div class="err-card"><div class="err-icon">⚡</div>'
            '<div class="err-title">Cannot Load Movies</div>'
            f'<div class="err-msg">Unable to reach the API at {esc(BACKEND_URL)}</div></div>',
            unsafe_allow_html=True)
        return

    # Search / filter
    search = st.text_input("Search movies", placeholder="🔍 Search for a movie...",
                           label_visibility="collapsed", key="home_search")

    if search:
        # When searching, filter all movies
        display_movies = [m for m in all_movies if search.lower() in m.lower()][:60]
    else:
        # Default: show popular movies
        display_movies = fetch_popular_movies(60)
        if not display_movies:
            display_movies = all_movies[:60]

    if not display_movies:
        st.markdown('<div class="prompt-card"><div class="p-icon">🔍</div>'
                    '<div class="p-text">No movies match your search.</div></div>',
                    unsafe_allow_html=True)
        return

    if not search:
        st.markdown('<p style="color:rgba(255,255,255,0.3);font-size:0.8rem;text-align:center;margin-bottom:0.5rem;">'
                    '🔥 Popular Movies</p>', unsafe_allow_html=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        posters = dict(zip(display_movies, pool.map(fetch_poster_url, display_movies)))

    # Render grid — each card is a clickable <a> link using query params
    COLS = 6
    rows = [display_movies[i:i + COLS] for i in range(0, len(display_movies), COLS)]
    for row_movies in rows:
        cols = st.columns(COLS)
        for i, title in enumerate(row_movies):
            with cols[i]:
                poster_url = posters.get(title)
                if poster_url:
                    poster_html = f'<img src="{poster_url}" alt="{esc(title)}" style="width:100%;aspect-ratio:2/3;object-fit:cover;display:block;border-radius:6px;">'
                else:
                    poster_html = '<div style="width:100%;aspect-ratio:2/3;background:linear-gradient(135deg,#1e1e2e,#252540);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:2.5rem;opacity:0.2;">🎬</div>'

                movie_url = f"?page=detail&movie={urllib.parse.quote(title)}"
                st.markdown(
                    f'<a href="{movie_url}" target="_self" class="mgrid-link">'
                    f'<div class="mgrid-card"><div class="mgrid-poster">{poster_html}</div>'
                    f'<div class="mgrid-title">{esc(title)}</div></div></a>',
                    unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  PAGE: Movie Detail — Hero + Recommendations
# ═══════════════════════════════════════════════════════════════════
def render_detail():
    render_header()

    selected = st.query_params.get("movie", "")
    if not selected:
        st.query_params.clear()
        st.rerun()
        return

    # Back button — HTML link back to homepage
    st.markdown(
        '<a href="/" target="_self" class="back-btn">← Back to Browse</a>',
        unsafe_allow_html=True)

    # Fetch recommendations
    with st.spinner("Finding the perfect movies for you…"):
        try:
            resp = requests.post(f"{BACKEND_URL}/recommend",
                                 json={"movie": selected, "n": 10}, timeout=30)
            if resp.status_code == 404:
                detail = resp.json().get("detail", "Movie not found.")
                st.markdown(f'<div class="err-card"><div class="err-icon">🔍</div>'
                            f'<div class="err-title">Movie Not Found</div>'
                            f'<div class="err-msg">{esc(detail)}</div></div>',
                            unsafe_allow_html=True)
                return
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            st.markdown(f'<div class="err-card"><div class="err-icon">⚡</div>'
                        f'<div class="err-title">Connection Error</div>'
                        f'<div class="err-msg">Cannot reach the API at {esc(BACKEND_URL)}</div></div>',
                        unsafe_allow_html=True)
            return
        except Exception as exc:
            st.markdown(f'<div class="err-card"><div class="err-icon">⚠️</div>'
                        f'<div class="err-title">Something Went Wrong</div>'
                        f'<div class="err-msg">{esc(str(exc))}</div></div>',
                        unsafe_allow_html=True)
            return

    # Hero section
    input_info = data.get("input_movie_info")
    if input_info:
        render_hero(input_info)

    # Recommendations
    recs = data.get("recommendations", [])
    if recs:
        st.markdown('<div class="genre-row-title" style="font-size:1.6rem;margin-top:2rem;">More Like This</div>',
                    unsafe_allow_html=True)

        # All recommendations row
        render_genre_row("Recommended For You", recs)

        # Genre-grouped rows
        genre_groups = group_by_genre(recs)
        for genre_name, genre_movies in genre_groups.items():
            if len(genre_movies) >= 2:
                render_genre_row(genre_name, genre_movies)

        # Clickable recommendation grid — each card links to its detail page
        st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)
        COLS = 6
        rec_rows = [recs[i:i + COLS] for i in range(0, len(recs), COLS)]
        for row_movies in rec_rows:
            cols = st.columns(COLS)
            for i, movie in enumerate(row_movies):
                with cols[i]:
                    t = movie.get("title", "Unknown")
                    poster_url = fetch_poster_url(t)
                    if poster_url:
                        p_html = f'<img src="{poster_url}" alt="{esc(t)}" style="width:100%;aspect-ratio:2/3;object-fit:cover;display:block;border-radius:6px;">'
                    else:
                        p_html = '<div style="width:100%;aspect-ratio:2/3;background:linear-gradient(135deg,#1e1e2e,#252540);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:2.5rem;opacity:0.2;">🎬</div>'
                    movie_url = f"?page=detail&movie={urllib.parse.quote(t)}"
                    st.markdown(
                        f'<a href="{movie_url}" target="_self" class="mgrid-link">'
                        f'<div class="mgrid-card"><div class="mgrid-poster">{p_html}</div>'
                        f'<div class="mgrid-title">{esc(t)}</div></div></a>',
                        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
def personal_api(method, path, **kwargs):
    response = requests.request(method, f"{BACKEND_URL}/personal{path}", timeout=30, **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", "Request failed")
        except ValueError:
            detail = "API returned an invalid response. Check the backend logs."
        raise ValueError(str(detail))
    return response.json()


def render_personal():
    render_header()
    st.subheader("For You")
    st.caption("Rate movies to discover what people with similar tastes enjoyed. Local demo profiles are shared on this machine; use nicknames.")
    try:
        profiles = personal_api("GET", "/users")["users"]
        with st.expander("Create a local profile", expanded=not profiles):
            with st.form("create_profile"):
                name = st.text_input("Profile nickname", max_chars=60)
                if st.form_submit_button("Create profile"):
                    created = personal_api("POST", "/users", json={"name": name})
                    st.session_state["active_profile"] = created["id"]
                    st.rerun()
        if not profiles:
            st.info("Create a profile to start rating. No sign-in is required.")
            return
        labels = {p["id"]: f'{p["name"]} (#{p["id"]})' for p in profiles}
        user_id = st.selectbox("Your profile", list(labels), format_func=labels.get, key="active_profile")
        history = personal_api("GET", f"/users/{user_id}/ratings")["ratings"]
        st.caption(f"{len(history)} movies rated. Rate at least three with varied scores to find similar viewers; more overlap improves support.")
        with st.expander("Rate a movie or update a rating", expanded=True):
            query = st.text_input("Search MovieLens titles", placeholder="Toy Story, Inception…")
            catalog = personal_api("GET", "/movies", params={"q": query, "n": 100})["movies"]
            if catalog:
                choices = {m["movie_id"]: f'{m["title"]} · #{m["movie_id"]}' for m in catalog}
                movie_id = st.selectbox("Movie", list(choices), format_func=choices.get)
                current = next((r["rating"] for r in history if r["movie_id"] == movie_id), 3.0)
                with st.form(f"rating_{user_id}_{movie_id}"):
                    rating = st.slider("Your rating (stars)", 0.5, 5.0, float(current), 0.5)
                    if st.form_submit_button("Save rating"):
                        personal_api("PUT", f"/users/{user_id}/ratings", json={"movie_id": movie_id, "rating": rating})
                        st.rerun()
            else:
                st.info("No matching MovieLens titles. Try another search.")
        with st.expander("Your saved ratings"):
            if history:
                st.dataframe([{"Movie": r["title"], "Stars": r["rating"]} for r in history], hide_index=True, use_container_width=True)
            else:
                st.info("No ratings yet. Suggestions below use community ratings.")
        st.button("Refresh recommendations")
        with st.spinner("Comparing movie ratings…"):
            result = personal_api("GET", f"/users/{user_id}/recommendations", params={"n": 10})
        strategy = result["strategy"]
        if strategy == "popularity":
            st.info("Community picks: there is not enough shared rating evidence for personal recommendations yet.")
        elif strategy == "mixed":
            st.info("Personal recommendations with community picks where neighbor evidence is insufficient. Each result shows its source.")
        elif strategy == "collaborative":
            st.caption(f'Based on rating patterns from {result["neighbor_count"]} similar viewers.')
        if not result["recommendations"]:
            st.info("No unseen movies with rating evidence remain.")
        recommendations = result["recommendations"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            sources = list(pool.map(
                lambda movie: poster_source(movie["title"], movie.get("tmdb_id"), movie.get("poster_url", "")),
                recommendations,
            ))
        for movie, source in zip(recommendations, sources):
            poster, details = st.columns([1, 5])
            with poster:
                if source:
                    st.markdown(f'<img src="{source}" alt="{esc(movie["title"])} poster" width="90">', unsafe_allow_html=True)
                else:
                    st.caption("🎬 Poster unavailable")
            with details:
                st.write(f'**{movie["title"]}**')
                st.caption(movie["genres"])
                source = "Similar viewers" if movie["source"] == "collaborative" else "Community rating fallback"
                st.write(f'{source} · score {movie["score"]:.2f}/5 · {movie["rating_count"]} ratings')
                st.caption(f'MovieLens ID {movie["movie_id"]}. Scores are estimates, not guaranteed enjoyment.')
    except (requests.RequestException, ValueError) as exc:
        logging.getLogger(__name__).warning("Personal recommendations request failed: %s", exc)
        if isinstance(exc, requests.ConnectionError):
            st.error("Cannot connect to the recommendation service. It may still be starting. Wait a moment, then retry.")
        elif isinstance(exc, requests.Timeout):
            st.error("The recommendation service took too long to respond. Please retry.")
        else:
            st.error(f"Personal recommendations unavailable: {exc}")
        if st.button("Retry connection"):
            st.rerun()


def main():
    inject_css()

    # Read navigation from URL query params
    page = st.query_params.get("page", "home")

    if page == "detail":
        render_detail()
    else:
        section = st.radio("Explore MovieMind", ["For You", "Browse Movies"], horizontal=True)
        if section == "For You":
            render_personal()
        else:
            render_home()

    st.markdown('<div class="mm-footer">Built with ♥ using FastAPI &amp; Streamlit · Personalized with Collaborative Filtering · More Like This uses TF-IDF</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
