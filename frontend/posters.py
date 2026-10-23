"""Reuse catalog posters and recover stale URLs through TMDB when configured."""
import base64
import logging
import os
from pathlib import Path
import re
from functools import lru_cache

import pandas as pd
import requests
import streamlit as st
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
IMAGE_BASE = 'https://image.tmdb.org/t/p/w342'
API_BASE = 'https://api.themoviedb.org/3'
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def local_posters():
    path = ROOT / 'Datset' / 'movies_metadata.csv'
    if not path.exists():
        return {}
    movies = pd.read_csv(path, usecols=['id', 'title', 'poster_path'], low_memory=False)
    movies['id'] = pd.to_numeric(movies.id, errors='coerce')
    movies = movies.dropna(subset=['id', 'title']).drop_duplicates('title')
    return {row.title.casefold(): (int(row.id), row.poster_path if isinstance(row.poster_path, str) else '')
            for row in movies.itertuples()}


def api_key():
    # Re-read configuration so a newly added key works without a server restart.
    return os.getenv('TMDB_API_KEY') or dotenv_values(ROOT / '.env').get('TMDB_API_KEY', '') or ''


@st.cache_data(ttl=300, show_spinner=False)
def image_source(path):
    if not isinstance(path, str) or not re.fullmatch(r'/[A-Za-z0-9_.-]+', path):
        return None
    try:
        response = requests.get(IMAGE_BASE + path, timeout=(2, 4))
        if response.status_code != 200:
            logger.info('Poster image unavailable (HTTP %s)', response.status_code)
            return None
        mime = response.headers.get('Content-Type', '').split(';')[0].lower()
        if mime not in ('image/jpeg', 'image/png', 'image/webp') or not response.content:
            return None
        if len(response.content) > 5_000_000:
            return None
        return f'data:{mime};base64,' + base64.b64encode(response.content).decode('ascii')
    except requests.RequestException as exc:
        logger.warning('Poster image request failed (%s)', type(exc).__name__)
        return None


@st.cache_data(ttl=300, show_spinner=False)
def tmdb_poster_path(title, tmdb_id, key):
    if not key:
        return None
    params = {'api_key': key}
    if tmdb_id:
        endpoint = f'/movie/{int(tmdb_id)}'
    else:
        endpoint = '/search/movie'
        match = re.fullmatch(r'(.*?)\s*\((\d{4})\)', title)
        params['query'] = match.group(1) if match else title
        if match:
            params['year'] = match.group(2)
    try:
        response = requests.get(API_BASE + endpoint, params=params, timeout=(2, 4))
        if response.status_code != 200:
            # Never log request URLs or exception strings: they may contain the key.
            logger.warning('TMDB poster lookup failed (HTTP %s)', response.status_code)
            return None
        payload = response.json()
        if tmdb_id:
            return payload.get('poster_path')
        for movie in payload.get('results', []):
            if str(movie.get('title', '')).casefold() == params['query'].casefold():
                if 'year' not in params or movie.get('release_date', '').startswith(params['year']):
                    return movie.get('poster_path')
    except (requests.RequestException, ValueError) as exc:
        logger.warning('TMDB poster lookup failed (%s)', type(exc).__name__)
    return None


def poster_source(title, tmdb_id=None, poster_url=''):
    path = ''
    if poster_url.startswith('https://image.tmdb.org/t/p/'):
        path = '/' + poster_url.rsplit('/', 1)[-1]
    if not tmdb_id and not poster_url:
        tmdb_id, local_path = local_posters().get(title.casefold(), (None, ''))
        path = path or local_path
    if path:
        source = image_source(path)
        if source:
            return source
    updated_path = tmdb_poster_path(title, tmdb_id, api_key())
    if updated_path and updated_path != path:
        return image_source(updated_path)
    return None
