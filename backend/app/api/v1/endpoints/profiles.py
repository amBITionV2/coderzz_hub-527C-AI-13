"""
Profile endpoints for oceanographic profile data management.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Profile, Float, Measurement
from app.schemas import (
    ProfileSchema,
    ProfileSummary,
    PaginatedResponse,
    ErrorResponse
)
from app.services.geospatial import geospatial_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size"),
    float_id: Optional[int] = Query(None, description="Filter by float ID"),
    wmo_id: Optional[str] = Query(None, description="Filter by float WMO ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    min_lat: Optional[float] = Query(None, ge=-90, le=90, description="Minimum latitude"),
    max_lat: Optional[float] = Query(None, ge=-90, le=90, description="Maximum latitude"),
    min_lon: Optional[float] = Query(None, ge=-180, le=180, description="Minimum longitude"),
    max_lon: Optional[float] = Query(None, ge=-180, le=180, description="Maximum longitude"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse:
    """
    Get paginated list of profiles with optional filtering.
    
    Supports filtering by:
    - Float ID or WMO ID
    - Date range
    - Geographic bounding box
    """
    try:
        # Build base query
        query = select(Profile).join(Float)
        count_query = select(func.count(Profile.id)).select_from(Profile).join(Float)
        
        # Apply filters
        filters = []
        
        if float_id:
            filters.append(Profile.float_id == float_id)
        
        if wmo_id:
            filters.append(Float.wmo_id == wmo_id)
        
        if start_date:
            filters.append(Profile.timestamp >= start_date)
        
        if end_date:
            filters.append(Profile.timestamp <= end_date)
        
        if min_lat is not None:
            filters.append(Profile.latitude >= min_lat)
        
        if max_lat is not None:
            filters.append(Profile.latitude <= max_lat)
        
        if min_lon is not None:
            filters.append(Profile.longitude >= min_lon)
        
        if max_lon is not None:
            filters.append(Profile.longitude <= max_lon)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        offset = (page - 1) * size
        result = await db.execute(
            query.offset(offset).limit(size).order_by(Profile.timestamp.desc())
        )
        profiles = result.scalars().all()
        
        # Convert to summary schemas
        profile_summaries = []
        for profile in profiles:
            # Count measurements
            measurement_count = await geospatial_service._count_measurements(db, profile.id)
            
            summary = ProfileSummary(
                id=profile.id,
                cycle_number=profile.cycle_number,
                timestamp=profile.timestamp,
                latitude=profile.latitude,
                longitude=profile.longitude,
                measurement_count=measurement_count
            )
            profile_summaries.append(summary)
        
        return PaginatedResponse(
            items=profile_summaries,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/{profile_id}", response_model=ProfileSchema)
async def get_profile(
    profile_id: int,
    include_measurements: bool = Query(True, description="Include measurement data"),
    db: AsyncSession = Depends(get_db)
) -> ProfileSchema:
    """
    Get detailed information about a specific profile.
    
    Optionally includes all measurement data (temperature, salinity, etc.)
    for the profile.
    """
    try:
        # Build query
        query = select(Profile).where(Profile.id == profile_id)
        
        if include_measurements:
            query = query.options(selectinload(Profile.measurements))
        
        result = await db.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Profile {profile_id} not found"}
            )
        
        return ProfileSchema.from_orm(profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile {profile_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/region/bbox", response_model=List[ProfileSummary])
async def get_profiles_in_bbox(
    min_lon: float = Query(..., ge=-180, le=180, description="Minimum longitude"),
    min_lat: float = Query(..., ge=-90, le=90, description="Minimum latitude"),
    max_lon: float = Query(..., ge=-180, le=180, description="Maximum longitude"),
    max_lat: float = Query(..., ge=-90, le=90, description="Maximum latitude"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of profiles"),
    db: AsyncSession = Depends(get_db)
) -> List[ProfileSummary]:
    """
    Get profiles within a geographic bounding box.
    
    Uses PostGIS spatial queries for efficient geographic filtering.
    Optionally filters by date range.
    """
    try:
        # Validate bounding box
        if min_lon >= max_lon or min_lat >= max_lat:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid Bounding Box", "message": "Invalid bounding box coordinates"}
            )
        
        bbox = [min_lon, min_lat, max_lon, max_lat]
        
        profiles = await geospatial_service.get_profiles_in_region(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return profiles
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profiles in bbox: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Query Error", "message": str(e)}
        )


@router.get("/{profile_id}/measurements")
async def get_profile_measurements(
    profile_id: int,
    variable: Optional[str] = Query(None, description="Filter by variable name"),
    min_pressure: Optional[float] = Query(None, ge=0, description="Minimum pressure (dbar)"),
    max_pressure: Optional[float] = Query(None, ge=0, description="Maximum pressure (dbar)"),
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Get measurements for a specific profile.
    
    Supports filtering by:
    - Variable type (temperature, salinity, etc.)
    - Pressure/depth range
    """
    try:
        # Check if profile exists
        profile_result = await db.execute(
            select(Profile).where(Profile.id == profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Profile {profile_id} not found"}
            )
        
        # Build measurement query
        query = select(Measurement).where(Measurement.profile_id == profile_id)
        
        # Apply pressure filters
        if min_pressure is not None:
            query = query.where(Measurement.pressure >= min_pressure)
        
        if max_pressure is not None:
            query = query.where(Measurement.pressure <= max_pressure)
        
        # Order by pressure (depth)
        query = query.order_by(Measurement.pressure)
        
        result = await db.execute(query)
        measurements = result.scalars().all()
        
        # Convert to dictionaries and optionally filter by variable
        measurement_data = []
        for measurement in measurements:
            data = {
                "id": measurement.id,
                "pressure": measurement.pressure,
                "depth": measurement.depth,
                "measurement_order": measurement.measurement_order
            }
            
            # Add variables
            variables = {
                "temperature": measurement.temperature,
                "salinity": measurement.salinity,
                "dissolved_oxygen": measurement.dissolved_oxygen,
                "ph": measurement.ph,
                "nitrate": measurement.nitrate,
                "chlorophyll": measurement.chlorophyll
            }
            
            # Filter by specific variable if requested
            if variable:
                if variable in variables and variables[variable] is not None:
                    data[variable] = variables[variable]
                else:
                    continue  # Skip this measurement if variable not available
            else:
                # Include all available variables
                for var_name, var_value in variables.items():
                    if var_value is not None:
                        data[var_name] = var_value
            
            measurement_data.append(data)
        
        return measurement_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting measurements for profile {profile_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/{profile_id}/statistics")
async def get_profile_statistics(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get statistical summary for a profile's measurements.
    
    Returns statistics for each available variable including:
    - Count, mean, min, max, standard deviation
    - Depth range and measurement distribution
    """
    try:
        # Check if profile exists
        profile_result = await db.execute(
            select(Profile).where(Profile.id == profile_id).options(
                selectinload(Profile.measurements)
            )
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Profile {profile_id} not found"}
            )
        
        measurements = profile.measurements
        
        stats = {
            "profile_id": profile_id,
            "cycle_number": profile.cycle_number,
            "timestamp": profile.timestamp,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "measurement_count": len(measurements),
            "variables": {}
        }
        
        if measurements:
            # Pressure/depth statistics
            pressures = [m.pressure for m in measurements if m.pressure is not None]
            if pressures:
                stats["depth_range"] = {
                    "min_pressure": min(pressures),
                    "max_pressure": max(pressures),
                    "pressure_count": len(pressures)
                }
            
            # Variable statistics
            variables = ["temperature", "salinity", "dissolved_oxygen", "ph", "nitrate", "chlorophyll"]
            
            for var_name in variables:
                values = [getattr(m, var_name) for m in measurements if getattr(m, var_name) is not None]
                
                if values:
                    import statistics
                    
                    var_stats = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.mean(values)
                    }
                    
                    if len(values) > 1:
                        var_stats["stddev"] = statistics.stdev(values)
                        var_stats["median"] = statistics.median(values)
                    
                    stats["variables"][var_name] = var_stats
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics for profile {profile_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Statistics Error", "message": str(e)}
        )


@router.get("/float/{float_id}/latest")
async def get_latest_profiles(
    float_id: int,
    limit: int = Query(10, ge=1, le=100, description="Number of latest profiles"),
    db: AsyncSession = Depends(get_db)
) -> List[ProfileSummary]:
    """
    Get the most recent profiles for a specific float.
    
    Returns profiles ordered by timestamp (most recent first).
    """
    try:
        # Check if float exists
        float_result = await db.execute(
            select(Float).where(Float.id == float_id)
        )
        float_obj = float_result.scalar_one_or_none()
        
        if not float_obj:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Float {float_id} not found"}
            )
        
        # Get latest profiles
        query = select(Profile).where(
            Profile.float_id == float_id
        ).order_by(
            Profile.timestamp.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        profiles = result.scalars().all()
        
        # Convert to summaries
        profile_summaries = []
        for profile in profiles:
            measurement_count = await geospatial_service._count_measurements(db, profile.id)
            
            summary = ProfileSummary(
                id=profile.id,
                cycle_number=profile.cycle_number,
                timestamp=profile.timestamp,
                latitude=profile.latitude,
                longitude=profile.longitude,
                measurement_count=measurement_count
            )
            profile_summaries.append(summary)
        
        return profile_summaries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest profiles for float {float_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )
