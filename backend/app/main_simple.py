"""
Simplified FastAPI main application for development without database.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time
import random
from datetime import datetime, timedelta

# Create FastAPI application
app = FastAPI(
    title="FloatChat Backend (Simplified)",
    version="1.0.0",
    description="Simplified Oceanographic AI Explorer Backend API for development",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class AIQueryInput(BaseModel):
    question: str
    context: Optional[dict] = None

class QueryParameters(BaseModel):
    location: Optional[str] = None
    bbox: Optional[List[float]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    variables: List[str] = []
    depth_range: Optional[List[float]] = None
    general_search_term: Optional[str] = None

class FloatSummary(BaseModel):
    id: int
    wmo_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str = "active"
    last_update: Optional[str] = None
    profile_count: int = 0
    latest_profile_date: Optional[str] = None

class MeasurementSchema(BaseModel):
    id: int
    profile_id: int
    pressure: float
    depth: Optional[float] = None
    temperature: Optional[float] = None
    salinity: Optional[float] = None
    dissolved_oxygen: Optional[float] = None
    ph: Optional[float] = None
    measurement_order: int = 0
    created_at: str
    updated_at: str

class ProfileSchema(BaseModel):
    id: int
    float_id: int
    cycle_number: int
    profile_id: str
    timestamp: str
    latitude: float
    longitude: float
    direction: str = "A"
    data_mode: str = "R"
    measurements: List[MeasurementSchema] = []
    created_at: str
    updated_at: str

class FloatDetail(BaseModel):
    id: int
    wmo_id: str
    deployment_latitude: Optional[float] = None
    deployment_longitude: Optional[float] = None
    platform_type: Optional[str] = None
    institution: Optional[str] = None
    project_name: Optional[str] = None
    pi_name: Optional[str] = None
    status: str = "active"
    deployment_date: Optional[str] = None
    last_update: Optional[str] = None
    profiles: List[ProfileSchema] = []
    created_at: str
    updated_at: str

class AIQueryResponse(BaseModel):
    query: str
    parameters: QueryParameters
    floats: List[FloatSummary]
    insights: str
    data_summary: dict
    recommendations: List[str]
    processing_time: float

# Sample data generator
def generate_sample_floats(count: int = 50) -> List[FloatSummary]:
    """Generate sample float data for development with realistic ocean positions."""
    floats = []
    institutions = ["WHOI", "SIO", "UW", "CSIRO", "BIO", "IFREMER", "JMA", "KORDI"]
    statuses = ["active", "active", "active", "maintenance", "inactive"]  # More active floats
    
    # Define realistic ocean regions with approximate boundaries
    ocean_regions = [
        # North Pacific
        {"lat_range": (10, 60), "lon_range": (-180, -120), "name": "North Pacific"},
        {"lat_range": (10, 60), "lon_range": (120, 180), "name": "North Pacific West"},
        
        # South Pacific  
        {"lat_range": (-60, -10), "lon_range": (-180, -70), "name": "South Pacific"},
        {"lat_range": (-60, -10), "lon_range": (120, 180), "name": "South Pacific West"},
        
        # North Atlantic
        {"lat_range": (10, 70), "lon_range": (-80, -10), "name": "North Atlantic"},
        
        # South Atlantic
        {"lat_range": (-60, -10), "lon_range": (-50, 20), "name": "South Atlantic"},
        
        # Indian Ocean
        {"lat_range": (-60, 30), "lon_range": (20, 120), "name": "Indian Ocean"},
        
        # Southern Ocean
        {"lat_range": (-70, -40), "lon_range": (-180, 180), "name": "Southern Ocean"},
        
        # Arctic Ocean (limited)
        {"lat_range": (70, 85), "lon_range": (-180, 180), "name": "Arctic Ocean"},
        
        # Mediterranean-like regions
        {"lat_range": (30, 45), "lon_range": (-10, 40), "name": "North Atlantic East"},
    ]
    
    for i in range(count):
        wmo_id = f"190{1000 + i}"
        
        # Select a random ocean region
        region = random.choice(ocean_regions)
        
        # Generate coordinates within that ocean region
        lat = random.uniform(region["lat_range"][0], region["lat_range"][1])
        lon = random.uniform(region["lon_range"][0], region["lon_range"][1])
        
        # Add some variation to avoid perfect grid patterns
        lat += random.uniform(-2, 2)
        lon += random.uniform(-5, 5)
        
        # Ensure coordinates stay within valid ranges
        lat = max(-85, min(85, lat))
        lon = max(-180, min(180, lon))
        
        float_data = FloatSummary(
            id=i + 1,
            wmo_id=wmo_id,
            latitude=lat,
            longitude=lon,
            status=random.choice(statuses),
            last_update=(datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat(),
            profile_count=random.randint(10, 200),
            latest_profile_date=(datetime.utcnow() - timedelta(days=random.randint(0, 7))).isoformat()
        )
        floats.append(float_data)
    
    return floats

def generate_sample_measurements(profile_id: int, count: int = 20) -> List[MeasurementSchema]:
    """Generate sample measurements for a profile."""
    measurements = []
    now = datetime.utcnow().isoformat()
    
    for i in range(count):
        pressure = i * 50 + random.uniform(0, 20)  # Increasing pressure with depth
        temperature = 20 - (pressure * 0.01) + random.uniform(-2, 2)  # Decreasing with depth
        salinity = 34.5 + random.uniform(-0.5, 0.5)
        
        measurement = MeasurementSchema(
            id=i + 1,
            profile_id=profile_id,
            pressure=pressure,
            depth=pressure * 0.98,
            temperature=temperature if random.random() > 0.1 else None,
            salinity=salinity if random.random() > 0.1 else None,
            dissolved_oxygen=random.uniform(150, 300) if random.random() > 0.3 else None,
            ph=random.uniform(7.8, 8.2) if random.random() > 0.5 else None,
            measurement_order=i,
            created_at=now,
            updated_at=now
        )
        measurements.append(measurement)
    
    return measurements

def generate_sample_profiles(float_id: int, count: int = 10) -> List[ProfileSchema]:
    """Generate sample profiles for a float."""
    profiles = []
    now = datetime.utcnow()
    
    for i in range(count):
        profile_date = now - timedelta(days=i * 10)
        lat = random.uniform(-70, 70)
        lon = random.uniform(-180, 180)
        
        profile = ProfileSchema(
            id=i + 1,
            float_id=float_id,
            cycle_number=i + 1,
            profile_id=f"FLOAT_{float_id}_CYCLE_{i+1:03d}",
            timestamp=profile_date.isoformat(),
            latitude=lat,
            longitude=lon,
            direction="A",
            data_mode="R",
            measurements=generate_sample_measurements(i + 1, random.randint(15, 25)),
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        )
        profiles.append(profile)
    
    return profiles

# No sample data - all floats removed

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to FloatChat API (Simplified Development Version)",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "note": "This is a simplified version for development without database dependencies"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": False,  # No database in simplified version
        "version": "1.0.0-simplified",
        "debug": "FLOATS REMOVED - EMPTY DATA VERSION"
    }

@app.post("/api/v1/query", response_model=AIQueryResponse)
async def process_ai_query(query_input: AIQueryInput) -> AIQueryResponse:
    """
    Process AI query (simplified version with mock responses).
    """
    start_time = time.time()
    
    # Simple parameter extraction based on keywords
    question = query_input.question.lower()
    
    # Extract location
    location = None
    if "pacific" in question:
        location = "Pacific Ocean"
    elif "atlantic" in question:
        location = "Atlantic Ocean"
    elif "indian" in question:
        location = "Indian Ocean"
    
    # Extract variables
    variables = []
    if "temperature" in question or "temp" in question:
        variables.append("temperature")
    if "salinity" in question or "salt" in question:
        variables.append("salinity")
    if "oxygen" in question:
        variables.append("dissolved_oxygen")
    
    # Create parameters
    parameters = QueryParameters(
        location=location,
        variables=variables,
        general_search_term=query_input.question if not variables and not location else None
    )
    
    # Filter floats based on simple criteria - NO FLOATS
    matching_floats = []  # Empty list - no sample floats
    
    # Simple location filtering
    if location:
        if "pacific" in location.lower():
            matching_floats = [f for f in matching_floats if f.longitude and f.longitude < -30]
        elif "atlantic" in location.lower():
            matching_floats = [f for f in matching_floats if f.longitude and -30 <= f.longitude <= 30]
        elif "indian" in location.lower():
            matching_floats = [f for f in matching_floats if f.longitude and f.longitude > 30]
    
    # Limit results
    matching_floats = matching_floats[:20]
    
    # Generate insights
    insights = f"🌊 **AI Analysis Results**\n\n"
    insights += f"Found {len(matching_floats)} oceanographic floats"
    if location:
        insights += f" in the {location}"
    if variables:
        insights += f" with {', '.join(variables)} measurements"
    insights += ".\n\n"
    
    if len(matching_floats) > 0:
        active_count = len([f for f in matching_floats if f.status == "active"])
        insights += f"📊 **Status Summary**: {active_count} active floats out of {len(matching_floats)} total.\n\n"
        
        if variables:
            insights += f"🔬 **Variables Available**: Monitoring {', '.join(variables)} across the selected region.\n\n"
    
    insights += "💡 **Note**: This is a simplified development version with simulated data."
    
    # Generate recommendations
    recommendations = [
        "Examine temporal trends in the selected region",
        "Compare data with historical averages",
        "Analyze vertical profiles for water mass characteristics"
    ]
    
    if variables:
        if "temperature" in variables:
            recommendations.append("Look for temperature anomalies indicating climate events")
        if "salinity" in variables:
            recommendations.append("Check salinity gradients for ocean circulation patterns")
    
    # Create data summary
    data_summary = {
        "float_count": len(matching_floats),
        "total_profiles": sum(f.profile_count for f in matching_floats),
        "query_parameters": parameters.dict(),
        "simulated": True
    }
    
    processing_time = time.time() - start_time
    
    return AIQueryResponse(
        query=query_input.question,
        parameters=parameters,
        floats=matching_floats,
        insights=insights,
        data_summary=data_summary,
        recommendations=recommendations,
        processing_time=processing_time
    )

@app.get("/api/v1/float/{wmo_id}", response_model=FloatDetail)
async def get_float_by_wmo_id(wmo_id: str) -> FloatDetail:
    """
    Get detailed float data by WMO ID (simplified version).
    """
    # Find float by WMO ID - NO FLOATS AVAILABLE
    float_data = None
    # No sample floats available - all removed
    
    # Always return 404 since no floats exist
    raise HTTPException(status_code=404, detail=f"Float with WMO ID {wmo_id} not found - no floats available")
    
    # Generate detailed float data
    now = datetime.utcnow().isoformat()
    profiles = generate_sample_profiles(float_data.id, random.randint(5, 15))
    
    institutions = ["Woods Hole Oceanographic Institution", "Scripps Institution of Oceanography", 
                   "University of Washington", "CSIRO", "Bedford Institute of Oceanography"]
    platforms = ["APEX", "SOLO", "PROVOR", "ARVOR", "NOVA"]
    
    detailed_float = FloatDetail(
        id=float_data.id,
        wmo_id=float_data.wmo_id,
        deployment_latitude=float_data.latitude,
        deployment_longitude=float_data.longitude,
        platform_type=random.choice(platforms),
        institution=random.choice(institutions),
        project_name="Argo Global Ocean Observing System",
        pi_name="Dr. Ocean Researcher",
        status=float_data.status,
        deployment_date=(datetime.utcnow() - timedelta(days=random.randint(100, 1000))).isoformat(),
        last_update=float_data.last_update,
        profiles=profiles,
        created_at=now,
        updated_at=now
    )
    
    return detailed_float

@app.get("/api/v1/floats")
@app.get("/api/v1/floats-empty")
async def get_floats(
    page: int = 1,
    size: int = 50,
    status: Optional[str] = None,
    wmo_id: Optional[str] = None
):
    """
    Get paginated list of floats (simplified version) - NO FLOATS.
    """
    import time
    
    # FORCE EMPTY RESPONSE - NO FLOATS SHOULD BE RETURNED
    return {
        "items": [],
        "total": 0,
        "page": page,
        "size": size,
        "pages": 0,
        "timestamp": time.time(),
        "message": "FLOATS COMPLETELY REMOVED - EMPTY RESPONSE",
        "debug": "This endpoint should return empty data"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
