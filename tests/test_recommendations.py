"""Hand-calculated fixtures test behavior, never used for training or reported metrics."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.collaborative import CollaborativeModel, clean_ratings, load_dataset
from backend.store import RatingStore
from backend.routes.personal import PersonalService
from scripts.evaluate import split_ratings


def fixture():
    movies = pd.DataFrame({'movieId': range(1, 7), 'title': ['A', 'B', 'C', 'D', 'E', 'Unrated'],
                           'genres': [''] * 6, 'poster_url': [''] * 6})
    rows = []
    for uid in range(1, 7):
        values = [5, 3, 1] if uid <= 3 else [1, 3, 5]
        for mid, rating in enumerate(values, 1):
            rows.append((uid, mid, rating, 100))
        if uid in (2, 3, 5, 6):
            rows.extend([(uid, 4, 5 if uid <= 3 else 1, 100), (uid, 5, 1 if uid <= 3 else 5, 100)])
    return movies, pd.DataFrame(rows, columns=['userId', 'movieId', 'rating', 'timestamp'])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.movies, self.ratings = fixture()
        self.model = CollaborativeModel(self.movies, self.ratings)

    def test_distinct_preferences_use_neighbors_and_filter_seen(self):
        left, right = self.model.recommend(1), self.model.recommend(4)
        self.assertEqual(left['recommendations'][0]['movie_id'], 4)
        self.assertEqual(right['recommendations'][0]['movie_id'], 5)
        self.assertEqual(left['recommendations'][0]['source'], 'collaborative')
        self.assertEqual(left['neighbor_count'], 2)
        self.assertFalse({1, 2, 3, 6} & {r['movie_id'] for r in left['recommendations']})
        scores = [r['score'] for r in left['recommendations']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_unknown_sparse_and_constant_users_fall_back(self):
        self.assertEqual(self.model.recommend(999)['strategy'], 'popularity')
        for values in ([5], [3, 3, 3]):
            additional = pd.DataFrame([(99, mid, r, 100) for mid, r in enumerate(values, 1)], columns=self.ratings.columns)
            model = CollaborativeModel(self.movies, pd.concat([self.ratings, additional]))
            result = model.recommend(99)
            self.assertEqual(result['strategy'], 'popularity')
            self.assertTrue(all(np.isfinite(r['score']) for r in result['recommendations']))

    def test_validation_deduplicates_latest_and_rejects_invalid(self):
        dirty = pd.DataFrame([(1, 1, 2, 1), (1, 1, 5, 2), (1, 999, 5, 3),
                              (2, 1, 7, 1), (2, 1, 3.2, 2), (0, 1, 5, 1), (2, 1, np.nan, 1)], columns=self.ratings.columns)
        cleaned = clean_ratings(dirty, self.movies.movieId)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.iloc[0].rating, 5)
        self.assertTrue(clean_ratings(dirty.iloc[:0], self.movies.movieId).empty)

    def test_empty_training_and_all_seen(self):
        empty = CollaborativeModel(self.movies, self.ratings.iloc[:0])
        self.assertEqual(empty.recommend(1)['recommendations'], [])
        small = CollaborativeModel(self.movies.iloc[:3], self.ratings[self.ratings.movieId <= 3])
        self.assertEqual(small.recommend(1)['strategy'], 'empty')

    def test_split_has_no_overlap_and_statistics_use_only_train(self):
        train, test = split_ratings(self.ratings)
        self.assertFalse(set(zip(train.userId, train.movieId)) & set(zip(test.userId, test.movieId)))
        self.assertEqual(len(train) + len(test), len(self.ratings))
        model = CollaborativeModel(self.movies, train)
        self.assertAlmostEqual(model.global_mean, train.rating.mean())
        self.assertEqual(int(model.matrix.sum()), int(train.rating.sum()))
        train2, test2 = split_ratings(self.ratings)
        pd.testing.assert_frame_equal(test, test2)

    def test_missing_data_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'download_movielens'):
                load_dataset(directory)


class StoreTests(unittest.TestCase):
    def test_persistence_upsert_and_refresh(self):
        movies, ratings = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ratings.sqlite3'
            store = RatingStore(path)
            user = store.create_user('Viewer')
            svc = PersonalService(movies, ratings, store)
            for mid, score in [(1, 5), (2, 3), (3, 1)]:
                store.rate(user['id'], mid, score)
            self.assertEqual(svc.recommendations(user['id'], 2)['recommendations'][0]['movie_id'], 4)
            for mid, score in [(1, 1), (3, 5)]:
                store.rate(user['id'], mid, score)
            self.assertEqual(svc.recommendations(user['id'], 2)['recommendations'][0]['movie_id'], 5)
            restored = RatingStore(path)
            self.assertEqual(len(restored.history(user['id'])), 3)
            self.assertEqual(restored.users()[0]['name'], 'Viewer')
            with self.assertRaises(KeyError):
                restored.history(999)


class ApiTests(unittest.TestCase):
    def test_profiles_ratings_errors_and_personalization(self):
        from backend.main import app
        movies, ratings = fixture()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'RATINGS_DB': str(Path(directory) / 'test.sqlite3')}):
            with patch('backend.main.load_dataset', return_value=(movies, ratings)), TestClient(app) as client:
                self.assertEqual(client.post('/personal/users', json={'name': '   '}).status_code, 422)
                uid = client.post('/personal/users', json={'name': 'Test'}).json()['id']
                route = f'/personal/users/{uid}'
                self.assertEqual(client.get(route + '/recommendations').json()['strategy'], 'popularity')
                for mid, value in [(1, 5), (2, 3), (3, 1)]:
                    self.assertEqual(client.put(route + '/ratings', json={'movie_id': mid, 'rating': value}).status_code, 200)
                result = client.get(route + '/recommendations').json()
                self.assertEqual(result['recommendations'][0]['movie_id'], 4)
                self.assertEqual(result['strategy'], 'collaborative')
                for rating in [0, 5.5, 3.2]:
                    self.assertEqual(client.put(route + '/ratings', json={'movie_id': 1, 'rating': rating}).status_code, 422)
                self.assertEqual(client.put(route + '/ratings', json={'movie_id': 999, 'rating': 4}).status_code, 404)
                self.assertEqual(client.get('/personal/users/999/ratings').status_code, 404)
                self.assertEqual(client.get('/personal/users/999999999999999999999999/ratings').status_code, 422)
                self.assertEqual(client.get(route + '/recommendations?n=0').status_code, 422)
                self.assertEqual(client.get('/personal/movies?q=Unrated').json()['movies'][0]['movie_id'], 6)
                self.assertEqual(len(client.get(route + '/ratings').json()['ratings']), 3)
                app.state.personal = None
                self.assertEqual(client.get('/personal/users').status_code, 503)

    def test_database_failure_returns_actionable_503(self):
        import sqlite3
        from backend.main import app
        movies, ratings = fixture()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'RATINGS_DB': str(Path(directory) / 'test.sqlite3')}):
            with patch('backend.main.load_dataset', return_value=(movies, ratings)), TestClient(app) as client:
                with patch.object(app.state.personal.store, 'users', side_effect=sqlite3.OperationalError('locked')):
                    self.assertEqual(client.get('/personal/users').status_code, 503)


if __name__ == '__main__':
    unittest.main()
