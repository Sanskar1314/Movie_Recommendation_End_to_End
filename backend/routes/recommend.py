"""
Recommendation API routes.
"""

from fastapi import APIRouter, HTTPException

from backend.schemas import RecommendRequest, RecommendResponse, MovieInfo
from backend.utils import get_recommendations, get_movie_info

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    summary="Get movie recommendations",
    description="Returns a list of similar movies based on TF-IDF cosine similarity.",
)
async def recommend(payload: RecommendRequest):
    """Return movie recommendations for the given title."""
    try:
        results = get_recommendations(payload.movie, payload.n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Get the input movie's own metadata for the hero section
    movie_info = get_movie_info(payload.movie)
    input_info = MovieInfo(**movie_info) if movie_info else None

    return RecommendResponse(
        input_movie=payload.movie,
        input_movie_info=input_info,
        recommendations=[MovieInfo(**r) for r in results],
    )
