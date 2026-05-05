"""
Pydantic schemas for request / response validation.
"""

from pydantic import BaseModel, Field


# ── Request ─────────────────────────────────────────────────────────
class RecommendRequest(BaseModel):
    """Payload for the /recommend endpoint."""

    movie: str = Field(
        ...,
        min_length=1,
        description="Title of the movie to get recommendations for.",
        json_schema_extra={"example": "Toy Story"},
    )
    n: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of recommendations to return (1–50).",
    )


# ── Response ────────────────────────────────────────────────────────
class MovieInfo(BaseModel):
    """Metadata for a single recommended movie."""

    title: str
    genres: str = ""
    vote_average: float = 0.0
    overview: str = ""
    tagline: str = ""
    popularity: float = 0.0


class RecommendResponse(BaseModel):
    """Response payload for /recommend."""

    input_movie: str
    input_movie_info: MovieInfo | None = None
    recommendations: list[MovieInfo]


class HealthResponse(BaseModel):
    """Response payload for /health."""

    status: str = "healthy"
    total_movies: int = 0
