"""
AI query endpoints for natural language oceanographic queries.
"""

import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
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


async def _handle_float_id_query(
    db: AsyncSession,
    float_id: int
) -> AIQueryResponse:
    """Handle queries for specific float IDs or WMO IDs."""
    from app.models import Float, Profile, Measurement
    from sqlalchemy import select, func, or_
    from app.schemas import QueryParameters
    
    # Query the specific float by ID or WMO ID
    result = await db.execute(
        select(Float).where(
            or_(
                Float.id == float_id,
                Float.wmo_id == str(float_id)
            )
        )
    )
    float_obj = result.scalar_one_or_none()
    
    if not float_obj:
        return AIQueryResponse(
            query=f"Float/WMO ID {float_id}",
            parameters=QueryParameters(),
            floats=[],
            insights=f"❌ Float with ID or WMO ID {float_id} not found in the database.\n\nPlease check the ID and try again.",
            data_summary={'float_count': 0},
            recommendations=[
                "Show me all active floats",
                "Find floats in Pacific Ocean",
                "What floats are available?"
            ],
            processing_time=0
        )
    
    # Get float summary
    float_summary = await geospatial_service._create_float_summary(float_obj, db)
    
    # Get profile count
    profile_count_result = await db.execute(
        select(func.count(Profile.id)).where(Profile.float_id == float_id)
    )
    profile_count = profile_count_result.scalar() or 0
    
    # Get latest profile data
    latest_profile_result = await db.execute(
        select(Profile)
        .where(Profile.float_id == float_id)
        .order_by(Profile.timestamp.desc())
        .limit(1)
    )
    latest_profile = latest_profile_result.scalar_one_or_none()
    
    # Build insights
    insights = f"📍 **Float {float_obj.wmo_id}** (ID: {float_id})\n\n"
    insights += f"**Status:** {float_obj.status.title()}\n"
    
    if latest_profile:
        insights += f"**Location:** {latest_profile.latitude:.2f}°, {latest_profile.longitude:.2f}°\n"
        insights += f"**Last Update:** {latest_profile.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
    
    insights += f"**Profiles:** {profile_count}\n"
    
    if float_obj.institution:
        insights += f"**Institution:** {float_obj.institution}\n"
    
    # Generate recommendations
    recommendations = [
        f"Show me temperature data for float {float_id}",
        f"What is the salinity for float {float_id}",
        "Show me all floats in this region",
        f"Compare float {float_id} with nearby floats"
    ]
    
    return AIQueryResponse(
        query=f"Float ID {float_id}",
        parameters=QueryParameters(),
        floats=[float_summary],
        insights=insights,
        data_summary={
            'float_count': 1,
            'profile_count': profile_count
        },
        recommendations=recommendations,
        processing_time=0
    )


async def _handle_comparison_query(
    db: AsyncSession,
    oceans: List[str],
    variables: List[str]
) -> AIQueryResponse:
    """Handle comparison queries between two oceans."""
    from app.schemas import QueryParameters
    
    if not variables:
        variables = ['temperature', 'salinity']  # Default variables for comparison
    
    results = {}
    all_floats = []
    
    # Query each ocean separately
    for ocean in oceans:
        params = QueryParameters(
            location=ocean,
            variables=variables,
            status=None,
            general_search_term=None
        )
        
        floats, data_summary = await geospatial_service.query_floats_by_parameters(
            parameters=params,
            limit=100
        )
        
        results[ocean] = {
            'floats': floats,
            'data_summary': data_summary,
            'float_count': len(floats)
        }
        all_floats.extend(floats)
    
    # Generate comparison insights
    insights = f"🔍 **Comparison between {' and '.join(oceans)}**\n\n"
    
    for ocean in oceans:
        result = results[ocean]
        insights += f"**{ocean}:**\n"
        insights += f"  • {result['float_count']} floats, {result['data_summary'].get('measurement_count', 0):,} measurements\n"
        
        if result['data_summary'].get('variable_statistics'):
            stats = result['data_summary']['variable_statistics']
            for var in variables:
                if var in stats:
                    var_stats = stats[var]
                    insights += f"  • {var.title()}: {var_stats['mean']:.2f} (range: {var_stats['min']:.2f} to {var_stats['max']:.2f})\n"
        insights += "\n"
    
    # Add comparison summary
    if len(oceans) == 2 and variables:
        insights += "**Key Differences:**\n"
        for var in variables:
            stats1 = results[oceans[0]]['data_summary'].get('variable_statistics', {}).get(var)
            stats2 = results[oceans[1]]['data_summary'].get('variable_statistics', {}).get(var)
            
            if stats1 and stats2:
                diff = stats1['mean'] - stats2['mean']
                higher = oceans[0] if diff > 0 else oceans[1]
                insights += f"  • {var.title()}: {higher} has {abs(diff):.2f} units higher average\n"
    
    # Highlight float IDs
    insights += f"\n\n💡 Comparing data from {len(all_floats)} total floats across regions"
    
    # Generate recommendations
    recommendations = [
        f"Show me only {variables[0]} data for {oceans[0]}",
        f"What is the pressure in {oceans[1]}",
        f"Compare temperature and salinity in {oceans[0]}",
        f"Compare {oceans[0]} with Indian Ocean"
    ]
    
    return AIQueryResponse(
        query=f"Compare {' and '.join(oceans)}",
        parameters=QueryParameters(variables=variables),
        floats=all_floats,
        insights=insights,
        data_summary={
            'float_count': len(all_floats),
            'comparison': True,
            'regions': oceans
        },
        recommendations=recommendations,
        processing_time=0
    )


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
        
        # Check if query is irrelevant (no parameters extracted)
        if (not parameters.location and not parameters.variables and 
            not parameters.status and not parameters.general_search_term):
            # Return rejection message
            processing_time = time.time() - start_time
            return AIQueryResponse(
                query=query_input.question,
                parameters=parameters,
                floats=[],
                insights="Sorry, I cannot help you with that. I specialize in oceanographic float data including temperature, salinity, and pressure measurements from the Pacific, Atlantic, and Indian Oceans. Please ask about ocean data!",
                data_summary={'float_count': 0, 'profile_count': 0, 'measurement_count': 0},
                recommendations=[
                    "Show me active floats",
                    "What is the temperature in Pacific Ocean",
                    "Compare salinity between Atlantic and Indian Ocean",
                    "Show me pressure data for Indian Ocean"
                ],
                processing_time=processing_time
            )
        
        # Handle float ID queries
        if parameters.general_search_term and parameters.general_search_term.startswith('FLOAT_ID:'):
            float_id_str = parameters.general_search_term.replace('FLOAT_ID:', '')
            try:
                float_id = int(float_id_str)
                float_results = await _handle_float_id_query(db, float_id)
                processing_time = time.time() - start_time
                float_results.processing_time = processing_time
                return float_results
            except ValueError:
                logger.error(f"Invalid float ID: {float_id_str}")
        
        # Handle comparison queries
        if parameters.general_search_term and parameters.general_search_term.startswith('COMPARISON:'):
            oceans = parameters.general_search_term.replace('COMPARISON:', '').split(',')
            comparison_results = await _handle_comparison_query(db, oceans, parameters.variables)
            processing_time = time.time() - start_time
            return comparison_results
        
        # Step 2: Query database for matching floats
        floats, data_summary = await geospatial_service.query_floats_by_parameters(
            parameters=parameters,
            limit=100
        )
        
        logger.info(f"Found {len(floats)} matching floats")
        
        # Step 3: Generate AI insights with float highlighting
        insights = await ai_service.generate_insights(
            query=query_input.question,
            parameters=parameters,
            data_summary=data_summary
        )
        
        # Add float IDs to insights for highlighting
        if floats:
            float_ids = [f.id for f in floats]
            insights += f"\n\n💡 Showing data from {len(floats)} floats (IDs: {', '.join(map(str, float_ids[:10]))}{'...' if len(floats) > 10 else ''})"
        
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
            detail=jsonable_encoder(error_response)
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
            detail=jsonable_encoder(ErrorResponse(
                error="Parameter Extraction Error",
                details=[ErrorDetail(message=f"Failed to extract parameters: {str(e)}", code="PARAM_ERROR")]
            ))
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
            detail=jsonable_encoder(ErrorResponse(
                error="Insight Generation Error",
                details=[ErrorDetail(message=f"Failed to generate insights: {str(e)}", code="INSIGHT_ERROR")]
            ))
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
