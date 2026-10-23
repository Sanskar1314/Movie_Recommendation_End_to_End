"""Local demonstration profiles. No authentication or network privacy boundary."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd


class UnknownProfileError(KeyError):
    pass


class RatingStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 60)
                );
                CREATE TABLE IF NOT EXISTS ratings (
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    movie_id INTEGER NOT NULL,
                    rating REAL NOT NULL CHECK(rating BETWEEN 0.5 AND 5 AND rating*2 = CAST(rating*2 AS INTEGER)),
                    timestamp INTEGER NOT NULL DEFAULT (unixepoch()),
                    PRIMARY KEY(user_id, movie_id)
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA foreign_keys=ON')
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def users(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT id, name FROM users ORDER BY id')]

    def create_user(self, name):
        with self.connect() as db:
            cursor = db.execute('INSERT INTO users(name) VALUES (?)', (name,))
            return {'id': cursor.lastrowid, 'name': name}

    def require_user(self, user_id):
        with self.connect() as db:
            if db.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone() is None:
                raise UnknownProfileError('Unknown local profile. Create or select a profile first.')

    def rate(self, user_id, movie_id, rating):
        self.require_user(user_id)
        with self.connect() as db:
            db.execute('''INSERT INTO ratings(user_id,movie_id,rating) VALUES (?,?,?)
                ON CONFLICT(user_id,movie_id) DO UPDATE SET rating=excluded.rating,timestamp=unixepoch()''',
                       (user_id, movie_id, rating))

    def history(self, user_id):
        self.require_user(user_id)
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT movie_id,rating,timestamp FROM ratings WHERE user_id=? ORDER BY timestamp DESC,movie_id', (user_id,))]

    def interactions(self):
        with self.connect() as db:
            return pd.read_sql_query('SELECT user_id AS userId,movie_id AS movieId,rating,timestamp FROM ratings', db)
