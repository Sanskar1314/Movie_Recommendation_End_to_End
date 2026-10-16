# MovieMind — Movie Recommendation System

A content-based movie recommender with a FastAPI backend and a Streamlit interface. MovieMind combines movie overviews, genres, and taglines into TF-IDF features, then ranks similar movies using cosine similarity.

## Features

- A browsable movie grid and movie-detail pages in Streamlit.
- Recommendations with title, genres, overview, tagline, rating, and popularity metadata.
- Case-insensitive title lookup and close-title suggestions when a title cannot be found.
- Optional poster lookup through the TMDB API.
- FastAPI health, movie-list, metadata, and recommendation endpoints.

## Prerequisites

Use Python 3.10 or newer, a virtual environment, and movie metadata with the columns `title`, `overview`, `genres`, `tagline`, `vote_average`, and `popularity`.

The current repository does **not** include the input CSV or the four pickle files required by the API. Generate them with the notebook before starting the backend.

## Install

```bash
git clone https://github.com/Sanskar1314/Movie_Recommendation_End_to_End.git
cd Movie_Recommendation_End_to_End
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt -r frontend/requirements.txt
python -m pip install jupyterlab nltk matplotlib seaborn
```

On Windows activate with `.venv\Scripts\activate`.

## Generate model artifacts

1. Place your movie metadata CSV at `notebook/Dataset/movies_metadata.csv`.
2. Start `jupyter lab` and open `notebook/movies.ipynb` with `notebook/` as the kernel working directory, matching its relative CSV path.
3. Run the cells in order. They clean metadata, build unigram/bigram TF-IDF features with a 50,000-feature cap, demonstrate recommendations, and export four pickle files.
4. Move the generated files into a root-level `pickle_files/` directory:

```text
pickle_files/
├── df.pkl
├── indices.pkl
├── tfidf.pkl
└── tfidf_matrix.pkl
```

If the notebook ran from `notebook/`, the move can be performed from the repository root:

```bash
mkdir -p pickle_files
mv notebook/df.pkl notebook/indices.pkl notebook/tfidf.pkl notebook/tfidf_matrix.pkl pickle_files/
```

The notebook downloads NLTK stopwords and WordNet resources. An alternative artifact directory can be supplied through `PICKLE_DIR`.

## Start the application

From the repository root, start the API:

```bash
uvicorn backend.main:app --reload --port 8000
```

In another terminal with the same environment activated:

```bash
streamlit run frontend/app.py
```

Open the Streamlit address printed in the terminal. API documentation is available at [localhost:8000/docs](http://localhost:8000/docs).

Optional root `.env` settings:

```dotenv
BACKEND_URL=http://localhost:8000
TMDB_API_KEY=your_tmdb_api_key
# PICKLE_DIR=/absolute/path/to/pickle_files
```

`BACKEND_URL` defaults to port 8000. TMDB credentials are optional and enable poster requests; local metadata and recommendation artifacts are still required.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service status and loaded movie count |
| `GET /movies` | Available movie titles |
| `GET /movies/popular?n=60` | Movies ordered by popularity |
| `GET /movie/{title}` | Metadata for one movie |
| `POST /recommend` | Similar movies; accepts `movie` and `n` (1–50) |

Example:

```bash
curl -X POST http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"movie":"Toy Story","n":5}'
```

## Source layout

- `notebook/movies.ipynb`: preprocessing and artifact generation.
- `backend/model_loader.py`: startup artifact loading.
- `backend/utils.py`: title resolution and cosine similarity.
- `backend/routes/recommend.py`: recommendation endpoint.
- `frontend/app.py`: Streamlit UI and optional poster fetching.

Use `backend.main:app` and `frontend/app.py` as the entry points. The root `app.py` is empty and root `main.py` contains imports only. Pickle files should be generated from a trusted source and used with compatible pandas/scikit-learn versions.
