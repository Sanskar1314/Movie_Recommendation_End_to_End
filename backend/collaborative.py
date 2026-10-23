"""Explicit-rating user neighborhoods. MovieLens IDs are never title indices."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / 'data' / 'ml-latest-small'


def clean_ratings(ratings: pd.DataFrame, movie_ids) -> pd.DataFrame:
    required = ['userId', 'movieId', 'rating', 'timestamp']
    if not set(required).issubset(ratings.columns):
        raise ValueError('ratings.csv requires userId,movieId,rating,timestamp.')
    ratings = ratings[required].apply(pd.to_numeric, errors='coerce').astype('float64')
    valid = np.isfinite(ratings).all(axis=1)
    valid &= (ratings[['userId', 'movieId', 'timestamp']] % 1 == 0).all(axis=1)
    valid &= (ratings.userId > 0) & (ratings.timestamp >= 0)
    valid &= ratings.movieId.isin(movie_ids) & ratings.rating.between(0.5, 5)
    valid &= ratings.rating.mul(2).mod(1).eq(0)
    ratings = ratings.loc[valid].copy()
    ratings[['userId', 'movieId', 'timestamp']] = ratings[['userId', 'movieId', 'timestamp']].astype('int64')
    return ratings.sort_values('timestamp', kind='stable').drop_duplicates(['userId', 'movieId'], keep='last').reset_index(drop=True)


def load_dataset(directory=DEFAULT_DATA):
    directory = Path(directory)
    try:
        movies = pd.read_csv(directory / 'movies.csv')
        ratings = pd.read_csv(directory / 'ratings.csv')
    except FileNotFoundError as exc:
        raise ValueError('MovieLens data missing. Run: python scripts/download_movielens.py') from exc
    if not {'movieId', 'title', 'genres'}.issubset(movies.columns):
        raise ValueError('movies.csv requires movieId,title,genres.')
    movies['movieId'] = pd.to_numeric(movies.movieId, errors='coerce')
    movies = movies.loc[movies.movieId.gt(0) & np.isfinite(movies.movieId) & movies.movieId.mod(1).eq(0) & movies.title.notna()].copy()
    movies.movieId = movies.movieId.astype('int64')
    movies = movies.drop_duplicates('movieId').reset_index(drop=True)
    movies.genres = movies.genres.fillna('').str.replace('|', ' · ', regex=False)
    ratings = clean_ratings(ratings, movies.movieId)
    if movies.empty or ratings.empty:
        raise ValueError('MovieLens contains no valid movies or ratings.')
    # Enrich only by verified TMDB identifiers, never by ambiguous titles.
    movies['poster_url'] = ''
    movies['tmdb_id'] = None
    links_path = directory / 'links.csv'
    if links_path.exists():
        links = pd.read_csv(links_path, usecols=['movieId', 'tmdbId'])
        ids = links.drop_duplicates('movieId').set_index('movieId').tmdbId
        movies['tmdb_id'] = movies.movieId.map(ids).map(lambda value: int(value) if pd.notna(value) else None).astype(object)
        movies.loc[movies.tmdb_id.isna(), 'tmdb_id'] = None
    metadata_path = ROOT / 'Datset' / 'movies_metadata.csv'
    if (directory / 'links.csv').exists() and metadata_path.exists():
        links = pd.read_csv(directory / 'links.csv', usecols=['movieId', 'tmdbId'])
        metadata = pd.read_csv(metadata_path, usecols=['id', 'poster_path'], low_memory=False)
        metadata['tmdbId'] = pd.to_numeric(metadata.id, errors='coerce')
        metadata = metadata.dropna(subset=['tmdbId']).drop_duplicates('tmdbId')
        enriched = links.merge(metadata[['tmdbId', 'poster_path']], on='tmdbId', how='left')
        posters = enriched.drop_duplicates('movieId').set_index('movieId').poster_path
        paths = movies.movieId.map(posters).fillna('')
        movies['poster_url'] = paths.map(lambda p: 'https://image.tmdb.org/t/p/w500' + p if isinstance(p, str) and p.startswith('/') else '')
    return movies, ratings


class CollaborativeModel:
    def __init__(self, movies, ratings, neighbors=40, min_overlap=3, shrinkage=10):
        self.movies = movies.set_index('movieId', drop=False).sort_index()
        self.movie_ids = self.movies.index.to_numpy()
        self.user_ids = np.sort(ratings.userId.unique())
        self.user_index = {int(uid): i for i, uid in enumerate(self.user_ids)}
        self.movie_index = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        rows = ratings.userId.map(self.user_index).to_numpy(dtype=int)
        cols = ratings.movieId.map(self.movie_index).to_numpy(dtype=int)
        self.matrix = csr_matrix((ratings.rating.to_numpy(float), (rows, cols)), shape=(len(self.user_ids), len(self.movie_ids)))
        self.present = self.matrix.copy()
        self.present.data[:] = 1
        self.squared = self.matrix.power(2)
        counts = np.asarray(self.present.sum(axis=1)).ravel()
        self.means = np.divide(np.asarray(self.matrix.sum(axis=1)).ravel(), counts, out=np.zeros(len(counts)), where=counts > 0)
        self.global_mean = float(ratings.rating.mean()) if len(ratings) else 3.0
        self.counts = np.asarray(self.present.sum(axis=0)).ravel()
        sums = np.asarray(self.matrix.sum(axis=0)).ravel()
        self.popularity = (sums + 10 * self.global_mean) / (self.counts + 10)
        self.neighbors, self.min_overlap, self.shrinkage = neighbors, min_overlap, shrinkage

    def scores(self, user_id):
        scores = self.popularity.copy()
        sources = np.full(len(scores), 'popularity', dtype=object)
        seen = np.zeros(len(scores), dtype=bool)
        if user_id not in self.user_index:
            return scores, sources, seen, 0
        row = self.user_index[user_id]
        target = self.matrix.getrow(row).toarray().ravel()
        seen = target > 0
        if seen.sum() < self.min_overlap:
            return scores, sources, seen, 0
        mask = seen.astype(float)
        overlap = np.asarray(self.present @ mask).ravel()
        sx = np.asarray(self.matrix @ mask).ravel()
        sy = np.asarray(self.present @ target).ravel()
        sxx = np.asarray(self.squared @ mask).ravel()
        syy = np.asarray(self.present @ (target * target)).ravel()
        sxy = np.asarray(self.matrix @ target).ravel()
        safe = np.maximum(overlap, 1)
        covariance = sxy - sx * sy / safe
        denominator = np.sqrt(np.maximum(0, sxx - sx * sx / safe) * np.maximum(0, syy - sy * sy / safe))
        similarity = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 1e-10)
        similarity *= overlap / (overlap + self.shrinkage)
        similarity[overlap < self.min_overlap] = 0
        similarity[row] = 0
        candidates = np.flatnonzero(similarity > 1e-10)
        nearest = candidates[np.argsort(-similarity[candidates], kind='stable')[:self.neighbors]]
        if not len(nearest):
            return scores, sources, seen, 0
        weights = similarity[nearest]
        neighbor_ratings = self.matrix[nearest]
        neighbor_present = self.present[nearest]
        residual = neighbor_ratings - neighbor_present.multiply(self.means[nearest, None])
        numerator = np.asarray(residual.T @ weights).ravel()
        denominator = np.asarray(neighbor_present.T @ weights).ravel()
        support = np.asarray(neighbor_present.sum(axis=0)).ravel()
        supported = (support >= 2) & (denominator > 0)
        scores[supported] = np.clip(self.means[row] + numerator[supported] / denominator[supported], 0.5, 5)
        sources[supported] = 'collaborative'
        return scores, sources, seen, len(nearest)

    def recommend(self, user_id, n=10, baseline=False):
        scores, sources, seen, neighbor_count = self.scores(user_id)
        if baseline:
            scores = self.popularity.copy()
            sources[:] = 'popularity'
        # No-rating movies stay searchable but lack evidence for recommendation.
        candidates = np.flatnonzero(~seen & (self.counts > 0))
        ranked = sorted(candidates, key=lambda i: (-scores[i], -self.counts[i], self.movie_ids[i]))[:n]
        records = []
        for i in ranked:
            movie = self.movies.loc[self.movie_ids[i]]
            records.append({'movie_id': int(self.movie_ids[i]), 'title': str(movie.title), 'genres': str(movie.genres),
                            'poster_url': str(movie.get('poster_url', '')),
                            'tmdb_id': int(movie.tmdb_id) if pd.notna(movie.get('tmdb_id')) else None,
                            'score': float(scores[i]),
                            'rating_count': int(self.counts[i]), 'source': str(sources[i])})
        used = {r['source'] for r in records}
        strategy = 'mixed' if len(used) > 1 else next(iter(used), 'empty')
        return {'strategy': strategy, 'neighbor_count': neighbor_count, 'rated_count': int(seen.sum()), 'recommendations': records}
