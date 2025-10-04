"""
FastAPI main application entry point for FloatChat backend.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import time
import logging

from app.config import settings
from app.database import init_db, close_db, get_db
from app.schemas import ErrorResponse, FloatDetailSchema, AIQueryInput, AIQueryResponse, FloatSummarySchema
from app.crud import (
    get_float_data_by_wmo_id, 
    find_floats_by_params,
    get_recent_measurements_for_anomaly_detection,
    get_latest_measurements_for_floats
)


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Oceanographic AI Explorer Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    error_response = ErrorResponse(
        error="Internal Server Error",
        details=[{
            "message": "An unexpected error occurred",
            "code": "INTERNAL_ERROR"
        }]
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down application")
    
    # Close database connections
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    from app.database import check_db_health
    from app.schemas import HealthCheck
    from datetime import datetime
    
    db_healthy = await check_db_health()
    
    return HealthCheck(
        status="healthy" if db_healthy else "unhealthy",
        timestamp=datetime.utcnow(),
        database=db_healthy,
        version=settings.APP_VERSION
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Float detail endpoint
@app.get("/api/v1/float/{wmo_id}", response_model=FloatDetailSchema)
async def get_float_by_wmo_id(
    wmo_id: str,
    db: AsyncSession = Depends(get_db)
) -> FloatDetailSchema:
    """
    Get detailed float data by WMO ID.
    
    Returns comprehensive float information including:
    - Float metadata (platform type, institution, etc.)
    - All profiles with timestamps and locations
    - All measurements (temperature, salinity, pressure, etc.)
    
    Args:
        wmo_id: WMO identifier of the float
        db: Database session dependency
        
    Returns:
        FloatDetailSchema: Complete float data with all relationships
        
    Raises:
        HTTPException: 404 if float not found
    """
    try:
        logger.info(f"API request for float WMO ID: {wmo_id}")
        
        # Fetch float data with all relationships
        float_data = await get_float_data_by_wmo_id(db, wmo_id)
        
        if not float_data:
            logger.warning(f"Float {wmo_id} not found")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Float Not Found",
                    "message": f"Float with WMO ID '{wmo_id}' was not found in the database",
                    "wmo_id": wmo_id
                }
            )
        
        logger.info(f"Successfully retrieved float {wmo_id} with {len(float_data.profiles)} profiles")
        
        # Convert to Pydantic schema
        return FloatDetailSchema.from_orm(float_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"Error retrieving float {wmo_id}: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": f"An error occurred while retrieving float data: {str(e)}",
                "wmo_id": wmo_id
            }
        )


# AI-driven query endpoint with Proactive Scientific Assistant
@app.post("/api/v1/query", response_model=AIQueryResponse)
async def process_intelligent_query(
    query_input: AIQueryInput,
    db: AsyncSession = Depends(get_db)
) -> AIQueryResponse:
    """
    AI-powered oceanographic data query with proactive scientific insights.
    
    This endpoint:
    1. Uses AI to extract structured parameters from natural language
    2. Searches the database for matching floats
    3. Performs proactive anomaly detection on oceanographic variables
    4. Returns comprehensive results with AI-generated insights
    
    Args:
        query_input: Natural language query about oceanographic data
        db: Database session dependency
        
    Returns:
        AIQueryResponse: Complete response with floats, insights, and recommendations
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing intelligent query: {query_input.question[:100]}...")
        
        # Step 1: Use AI to extract structured parameters
        from app.services.ai_query_service import ai_query_service
        
        parameters = await ai_query_service.process_ai_query(query_input.question)
        logger.info(f"AI extracted parameters: {parameters.dict()}")
        
        # Step 2: Search for matching floats
        matching_floats = await find_floats_by_params(db, parameters)
        
        # Convert to FloatSummarySchema objects
        float_summaries = []
        for float_data in matching_floats:
            summary = FloatSummarySchema(**float_data)
            float_summaries.append(summary)
        
        logger.info(f"Found {len(float_summaries)} matching floats")
        
        # Step 3: Proactive AI Scientific Assistant - Anomaly Detection
        insights = ""
        anomaly_insights = []
        
        if float_summaries and parameters.variables:
            # Check if we should perform anomaly detection
            anomaly_variables = [v for v in parameters.variables if v in ['temperature', 'salinity', 'dissolved_oxygen']]
            
            if anomaly_variables:
                logger.info(f"Performing anomaly detection for variables: {anomaly_variables}")
                
                float_ids = [f.id for f in float_summaries]
                
                # Get baseline data from recent measurements
                baseline_data = await get_recent_measurements_for_anomaly_detection(
                    db, float_ids, anomaly_variables, days_back=30
                )
                
                # Get latest measurements for the found floats
                latest_measurements = await get_latest_measurements_for_floats(
                    db, float_ids, anomaly_variables
                )
                
                # Perform anomaly detection
                anomalies = await _detect_anomalies(
                    baseline_data, latest_measurements, float_summaries, anomaly_variables
                )
                
                if anomalies:
                    anomaly_insights.extend(anomalies)
                    logger.info(f"Detected {len(anomalies)} anomalies")
        
        # Step 4: Generate comprehensive insights
        if anomaly_insights:
            insights = "🔬 **Proactive Scientific Analysis:**\n\n" + "\n".join(anomaly_insights)
        else:
            insights = await _generate_standard_insights(float_summaries, parameters)
        
        # Step 5: Generate data summary
        data_summary = _create_data_summary(float_summaries, parameters)
        
        # Step 6: Generate AI recommendations
        recommendations = await _generate_recommendations(parameters, float_summaries, anomaly_insights)
        
        processing_time = time.time() - start_time
        
        # Create comprehensive response
        response = AIQueryResponse(
            query=query_input.question,
            parameters=parameters,
            floats=float_summaries,
            insights=insights,
            data_summary=data_summary,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
        logger.info(f"Query processed successfully in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing intelligent query: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Query Processing Error",
                "message": f"Failed to process intelligent query: {str(e)}",
                "query": query_input.question
            }
        )


async def _detect_anomalies(
    baseline_data: dict,
    latest_measurements: dict,
    float_summaries: list,
    variables: list
) -> list:
    """
    Detect anomalies in oceanographic measurements.
    
    Args:
        baseline_data: Historical data for baseline statistics
        latest_measurements: Latest measurements from floats
        float_summaries: List of float summaries
        variables: Variables to analyze
        
    Returns:
        List of anomaly insight strings
    """
    import statistics
    
    anomalies = []
    
    try:
        # Create float lookup
        float_lookup = {f.id: f for f in float_summaries}
        
        for variable in variables:
            if variable not in baseline_data or len(baseline_data[variable]) < 10:
                continue
            
            # Calculate baseline statistics
            baseline_values = baseline_data[variable]
            mean_val = statistics.mean(baseline_values)
            std_val = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0
            
            if std_val == 0:
                continue
            
            # Check each float's latest measurement
            for float_id, measurements in latest_measurements.items():
                if variable not in measurements:
                    continue
                
                current_value = measurements[variable]
                z_score = abs(current_value - mean_val) / std_val
                
                # Anomaly threshold: 2 standard deviations
                if z_score > 2.0:
                    float_info = float_lookup.get(float_id)
                    if float_info:
                        direction = "high" if current_value > mean_val else "low"
                        
                        anomaly_text = (
                            f"🚨 **Anomaly Alert**: Float {float_info.wmo_id} shows unusually {direction} "
                            f"{variable.replace('_', ' ')} ({current_value:.2f}) - "
                            f"{z_score:.1f}σ from regional mean ({mean_val:.2f})"
                        )
                        
                        # Add scientific context
                        if variable == 'temperature' and direction == 'high':
                            anomaly_text += " - Possible marine heatwave or warm water intrusion"
                        elif variable == 'salinity' and direction == 'low':
                            anomaly_text += " - Possible freshwater input or precipitation event"
                        elif variable == 'dissolved_oxygen' and direction == 'low':
                            anomaly_text += " - Possible hypoxic conditions or biological activity"
                        
                        anomalies.append(anomaly_text)
        
        return anomalies
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        return []


async def _generate_standard_insights(float_summaries: list, parameters) -> str:
    """Generate standard insights when no anomalies are detected."""
    try:
        insights = []
        
        if float_summaries:
            insights.append(f"📊 Found {len(float_summaries)} active oceanographic floats matching your criteria.")
            
            # Spatial distribution insight
            if len(float_summaries) > 1:
                lats = [f.latitude for f in float_summaries if f.latitude]
                lons = [f.longitude for f in float_summaries if f.longitude]
                
                if lats and lons:
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    
                    insights.append(
                        f"🌍 Spatial coverage: {lat_range:.1f}° latitude × {lon_range:.1f}° longitude"
                    )
            
            # Temporal insight
            recent_floats = [f for f in float_summaries if f.latest_profile_date]
            if recent_floats:
                from datetime import datetime, timedelta
                recent_cutoff = datetime.utcnow() - timedelta(days=30)
                recent_count = sum(1 for f in recent_floats if f.latest_profile_date > recent_cutoff)
                
                insights.append(f"📅 {recent_count} floats have reported data in the last 30 days")
            
            # Variable-specific insights
            if hasattr(parameters, 'variables') and parameters.variables:
                var_text = ", ".join(parameters.variables)
                insights.append(f"🔬 Monitoring variables: {var_text}")
        
        else:
            insights.append("❌ No floats found matching your search criteria.")
            insights.append("💡 Try expanding your search area or adjusting time range.")
        
        return "\n".join(insights)
        
    except Exception as e:
        logger.error(f"Error generating standard insights: {e}")
        return "Analysis completed successfully."


def _create_data_summary(float_summaries: list, parameters) -> dict:
    """Create data summary dictionary."""
    try:
        summary = {
            "float_count": len(float_summaries),
            "total_profiles": sum(f.profile_count for f in float_summaries if f.profile_count),
            "query_parameters": parameters.dict() if hasattr(parameters, 'dict') else {}
        }
        
        if float_summaries:
            # Spatial extent
            lats = [f.latitude for f in float_summaries if f.latitude]
            lons = [f.longitude for f in float_summaries if f.longitude]
            
            if lats and lons:
                summary["spatial_extent"] = {
                    "min_latitude": min(lats),
                    "max_latitude": max(lats),
                    "min_longitude": min(lons),
                    "max_longitude": max(lons)
                }
            
            # Temporal extent
            dates = [f.latest_profile_date for f in float_summaries if f.latest_profile_date]
            if dates:
                summary["temporal_extent"] = {
                    "earliest_profile": min(dates),
                    "latest_profile": max(dates)
                }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating data summary: {e}")
        return {"float_count": len(float_summaries)}


async def _generate_recommendations(parameters, float_summaries: list, anomaly_insights: list) -> list:
    """Generate AI recommendations based on query results."""
    try:
        recommendations = []
        
        if anomaly_insights:
            recommendations.append("🔍 Investigate anomalous floats for potential oceanographic events")
            recommendations.append("📈 Compare with satellite data and regional climate indices")
            recommendations.append("🌊 Check for correlation with ocean current patterns")
        
        if float_summaries:
            if len(float_summaries) > 10:
                recommendations.append("📊 Consider filtering by specific regions for detailed analysis")
            
            # Variable-specific recommendations
            if hasattr(parameters, 'variables') and parameters.variables:
                if 'temperature' in parameters.variables:
                    recommendations.append("🌡️ Analyze temperature profiles for thermocline depth variations")
                if 'salinity' in parameters.variables:
                    recommendations.append("🧂 Examine salinity gradients for water mass identification")
                if 'dissolved_oxygen' in parameters.variables:
                    recommendations.append("💨 Monitor oxygen levels for marine ecosystem health")
        
        else:
            recommendations.append("🔄 Try expanding search criteria or different time periods")
            recommendations.append("🗺️ Consider broader geographic regions")
        
        # Add temporal recommendations
        if not (hasattr(parameters, 'start_date') and parameters.start_date):
            recommendations.append("📅 Add temporal constraints for seasonal analysis")
        
        return recommendations[:5]  # Limit to 5 recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return ["Continue exploring oceanographic data patterns"]


# Include API routers
from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
