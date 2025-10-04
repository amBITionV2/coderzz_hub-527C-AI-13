"""
AI query endpoints for natural language oceanographic queries.
"""

import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    AIQueryInput, 
    AIQueryResponse, 
    QueryParameters,
    ErrorResponse,
    ErrorDetail
)
from app.services.ai_service import ai_service
from app.services.geospatial import geospatial_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=AIQueryResponse)
async def process_ai_query(
    query_input: AIQueryInput,
    db: AsyncSession = Depends(get_db)
) -> AIQueryResponse:
    """
    Process natural language query about oceanographic data.
    
    This endpoint:
    1. Extracts structured parameters from natural language
    2. Queries the database for matching floats
    3. Generates AI insights about the data
    4. Returns comprehensive response with floats and analysis
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing AI query: {query_input.question[:100]}...")
        
        # Step 1: Extract structured parameters from natural language
        parameters = await ai_service.process_query(query_input)
        logger.info(f"Extracted parameters: {parameters.dict()}")
        
        # Step 2: Query database for matching floats
        floats, data_summary = await geospatial_service.query_floats_by_parameters(
            parameters=parameters,
            limit=100
        )
        
        logger.info(f"Found {len(floats)} matching floats")
        
        # Step 3: Generate AI insights
        insights = await ai_service.generate_insights(
            query=query_input.question,
            parameters=parameters,
            data_summary=data_summary
        )
        
        # Step 4: Generate recommendations
        recommendations = await ai_service.generate_recommendations(
            query=query_input.question,
            parameters=parameters,
            data_summary=data_summary
        )
        
        processing_time = time.time() - start_time
        
        # Create response
        response = AIQueryResponse(
            query=query_input.question,
            parameters=parameters,
            floats=floats,
            insights=insights,
            data_summary=data_summary,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
        logger.info(f"Query processed successfully in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing AI query: {e}", exc_info=True)
        
        error_response = ErrorResponse(
            error="Query Processing Error",
            details=[ErrorDetail(
                message=f"Failed to process query: {str(e)}",
                code="QUERY_ERROR"
            )]
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_response.dict()
        )


@router.post("/extract-parameters", response_model=QueryParameters)
async def extract_query_parameters(
    query_input: AIQueryInput
) -> QueryParameters:
    """
    Extract structured parameters from natural language query.
    
    This endpoint only performs parameter extraction without
    executing the database query. Useful for testing and
    query parameter validation.
    """
    try:
        logger.info(f"Extracting parameters from: {query_input.question[:100]}...")
        
        parameters = await ai_service.process_query(query_input)
        
        logger.info(f"Extracted parameters: {parameters.dict()}")
        return parameters
        
    except Exception as e:
        logger.error(f"Error extracting parameters: {e}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Parameter Extraction Error",
                "message": f"Failed to extract parameters: {str(e)}"
            }
        )


@router.post("/insights")
async def generate_insights_only(
    query: str,
    parameters: QueryParameters,
    data_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate AI insights for given query and data summary.
    
    This endpoint allows generating insights without going through
    the full query process. Useful when you already have the data
    and just need AI analysis.
    """
    try:
        logger.info(f"Generating insights for query: {query[:100]}...")
        
        insights = await ai_service.generate_insights(
            query=query,
            parameters=parameters,
            data_summary=data_summary
        )
        
        recommendations = await ai_service.generate_recommendations(
            query=query,
            parameters=parameters,
            data_summary=data_summary
        )
        
        return {
            "insights": insights,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Insight Generation Error",
                "message": f"Failed to generate insights: {str(e)}"
            }
        )


@router.get("/capabilities")
async def get_ai_capabilities() -> Dict[str, Any]:
    """
    Get information about AI service capabilities.
    
    Returns information about:
    - Available AI models
    - Supported query types
    - Parameter extraction capabilities
    - Example queries
    """
    return {
        "ai_service_available": ai_service.llm is not None,
        "supported_parameters": [
            "location",
            "bbox",
            "start_date",
            "end_date", 
            "variables",
            "depth_range",
            "general_search_term"
        ],
        "supported_variables": [
            "temperature",
            "salinity", 
            "pressure",
            "dissolved_oxygen",
            "ph",
            "nitrate",
            "chlorophyll"
        ],
        "example_queries": [
            "Show me temperature data from the Pacific Ocean in 2023",
            "Find floats with salinity measurements near 30°N, 140°W",
            "What are the oxygen levels in the Southern Ocean?",
            "Compare temperature profiles between 0-1000m depth",
            "Show recent data from Argo floats in the Atlantic"
        ],
        "query_tips": [
            "Be specific about location (ocean regions, coordinates, or place names)",
            "Mention time periods for temporal filtering",
            "Specify variables of interest (temperature, salinity, etc.)",
            "Include depth ranges for vertical profiling",
            "Use natural language - the AI will extract parameters"
        ]
    }
