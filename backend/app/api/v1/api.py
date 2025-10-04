"""
API v1 router aggregation for FloatChat backend.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import ai_query, floats, profiles

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    ai_query.router, 
    prefix="/ai", 
    tags=["AI Queries"]
)

api_router.include_router(
    floats.router, 
    prefix="/floats", 
    tags=["Floats"]
)

api_router.include_router(
    profiles.router, 
    prefix="/profiles", 
    tags=["Profiles"]
)
