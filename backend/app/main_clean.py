"""
FastAPI main application - Clean version without database dependencies.
Uses the same API structure as main.py but without dummy data.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import time
import logging
from datetime import datetime

# Import schemas (these don't require database)
from app.schemas import AIQueryInput, AIQueryResponse, FloatSummarySchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="FloatChat Backend (Clean)",
    version="1.0.0",
    description="Clean Oceanographic AI Explorer Backend API without database dependencies",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": False,  # No database in this version
        "version": "1.0.0-clean",
        "message": "Clean API without dummy data"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to FloatChat API (Clean Version)",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "note": "This is a clean version without database dependencies or dummy data"
    }

# AI Query endpoint (returns empty results)
@app.post("/api/v1/ai/query")
async def process_ai_query(query_input: AIQueryInput) -> AIQueryResponse:
    """
    Process AI query - returns empty results (no database).
    """
    start_time = time.time()
    
    # Simple response without database lookup
    processing_time = time.time() - start_time
    
    return AIQueryResponse(
        query=query_input.question,
        parameters={
            "location": None,
            "variables": [],
            "general_search_term": query_input.question
        },
        floats=[],  # Empty list - no data
        insights="🌊 **No Data Available**\n\nThis is a clean API version without database connections. No float data is currently available.",
        data_summary={
            "total_floats": 0,
            "active_floats": 0,
            "regions_covered": 0,
            "data_quality": "No data"
        },
        recommendations=[
            "Set up database connection to access real oceanographic data",
            "Configure data ingestion from Argo float network",
            "Enable AI analysis with proper data sources"
        ],
        processing_time=processing_time
    )

# Include API routers (but modify them to return empty data)
from fastapi import APIRouter

# Create a simple floats router that returns empty data
floats_router = APIRouter()

@floats_router.get("/")
async def get_floats(
    page: int = 1,
    size: int = 50,
    status: Optional[str] = None,
    wmo_id: Optional[str] = None
):
    """
    Get paginated list of floats - returns empty data (no database).
    """
    return {
        "items": [],
        "total": 0,
        "page": page,
        "size": size,
        "pages": 0,
        "message": "CLEAN API - No floats available (database-free version)",
        "api_version": "main_clean.py",
        "timestamp": time.time()
    }

@floats_router.get("/{wmo_id}")
async def get_float_by_wmo_id(wmo_id: str):
    """
    Get detailed float data by WMO ID - returns 404 (no database).
    """
    raise HTTPException(
        status_code=404, 
        detail=f"Float with WMO ID {wmo_id} not found - no database connection"
    )

# Include the floats router
app.include_router(floats_router, prefix="/api/v1/floats", tags=["Floats"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
