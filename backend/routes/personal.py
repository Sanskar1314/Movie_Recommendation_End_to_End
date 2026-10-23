"""Profile, rating and collaborative recommendation endpoints."""
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field, field_validator

from backend.collaborative import CollaborativeModel, clean_ratings

router = APIRouter(prefix='/personal', tags=['Personal recommendations'])
PositiveId = Annotated[int, Path(ge=1, le=2**63 - 1)]


class ProfileInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Enter a profile name.')
        return value


class RatingInput(BaseModel):
    movie_id: int = Field(gt=0, le=2**63 - 1, strict=True)
    rating: float = Field(ge=0.5, le=5, multiple_of=0.5, allow_inf_nan=False)


def service(request: Request):
    if request.app.state.personal is None:
        raise HTTPException(503, detail=request.app.state.personal_error)
    return request.app.state.personal


class PersonalService:
    def __init__(self, movies, ratings, store):
        self.movies, self.ratings, self.store = movies, ratings, store
        self.offset = int(ratings.userId.max())
        self.catalog = movies.set_index('movieId')

    def recommendations(self, user_id, n):
        self.store.require_user(user_id)
        local = self.store.interactions()
        local['userId'] += self.offset
        local = clean_ratings(local, self.movies.movieId)
        combined = pd.concat([self.ratings, local], ignore_index=True)
        model = CollaborativeModel(self.movies, combined)
        return {'user_id': user_id, **model.recommend(user_id + self.offset, n)}


@router.get('/movies')
def movies(q: str = Query('', max_length=200), n: int = Query(40, ge=1, le=100), svc=Depends(service)):
    catalog = svc.movies
    selected = catalog.loc[catalog.title.str.contains(q, case=False, regex=False)].head(n)
    return {'movies': [{'movie_id': int(row.movieId), 'title': row.title, 'genres': row.genres,
                        'poster_url': row.poster_url,
                        'tmdb_id': int(row.tmdb_id) if pd.notna(getattr(row, 'tmdb_id', None)) else None}
                       for row in selected.itertuples()], 'total': len(catalog)}


@router.get('/users')
def users(svc=Depends(service)):
    return {'users': svc.store.users()}


@router.post('/users', status_code=201)
def create_user(payload: ProfileInput, svc=Depends(service)):
    return svc.store.create_user(payload.name)


@router.get('/users/{user_id}/ratings')
def history(user_id: PositiveId, svc=Depends(service)):
    result = svc.store.history(user_id)
    for row in result:
        row['title'] = str(svc.catalog.loc[row['movie_id'], 'title']) if row['movie_id'] in svc.catalog.index else 'Movie no longer in catalog'
    return {'user_id': user_id, 'ratings': result}


@router.put('/users/{user_id}/ratings')
def rate(user_id: PositiveId, payload: RatingInput, svc=Depends(service)):
    svc.store.require_user(user_id)
    if payload.movie_id not in svc.catalog.index:
        raise HTTPException(404, detail='Unknown MovieLens movie ID. Search /personal/movies.')
    svc.store.rate(user_id, payload.movie_id, payload.rating)
    return {'user_id': user_id, 'movie_id': payload.movie_id, 'rating': payload.rating}


@router.get('/users/{user_id}/recommendations')
def recommend(user_id: PositiveId, n: int = Query(10, ge=1, le=50), svc=Depends(service)):
    return svc.recommendations(user_id, n)
