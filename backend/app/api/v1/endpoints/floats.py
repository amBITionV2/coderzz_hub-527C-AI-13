"""
Float endpoints for oceanographic float management.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Float, Profile
from app.schemas import (
    FloatDetailSchema,
    FloatSummarySchema, 
    FloatCreate,
    PaginatedResponse,
    ErrorResponse,
    ErrorDetail
)
from app.services.data_ingestion import ingestion_service
from app.services.geospatial import geospatial_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def get_floats(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by float status"),
    wmo_id: Optional[str] = Query(None, description="Filter by WMO ID"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse:
    """
    Get paginated list of floats with optional filtering.
    
    Returns summary information for each float including:
    - Basic metadata (WMO ID, status, institution)
    - Latest position and profile date
    - Profile count statistics
    """
    try:
        # Build base query
        query = select(Float).options(
            selectinload(Float.profiles)
        )
        
        # Apply filters
        if status:
            query = query.where(Float.status == status)
        if wmo_id:
            query = query.where(Float.wmo_id.ilike(f"%{wmo_id}%"))
        
        # Get total count
        count_query = select(func.count(Float.id))
        if status:
            count_query = count_query.where(Float.status == status)
        if wmo_id:
            count_query = count_query.where(Float.wmo_id.ilike(f"%{wmo_id}%"))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        offset = (page - 1) * size
        result = await db.execute(
            query.offset(offset).limit(size).order_by(Float.created_at.desc())
        )
        floats = result.scalars().all()
        
        # Convert to summary schemas
        float_summaries = []
        for float_obj in floats:
            summary = await geospatial_service._create_float_summary(float_obj)
            float_summaries.append(summary)
        
        return PaginatedResponse(
            items=float_summaries,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Error getting floats: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/{float_id}", response_model=FloatDetailSchema)
async def get_float(
    float_id: int,
    include_profiles: bool = Query(True, description="Include profile data"),
    include_measurements: bool = Query(False, description="Include measurement data"),
    db: AsyncSession = Depends(get_db)
) -> FloatDetailSchema:
    """
    Get detailed information about a specific float.
    
    Optionally includes:
    - Profile data (timestamps, positions, metadata)
    - Measurement data (temperature, salinity, pressure values)
    """
    try:
        # Build query with appropriate loading
        query = select(Float).where(Float.id == float_id)
        
        if include_profiles:
            if include_measurements:
                query = query.options(
                    selectinload(Float.profiles).selectinload(Profile.measurements)
                )
            else:
                query = query.options(selectinload(Float.profiles))
        
        result = await db.execute(query)
        float_obj = result.scalar_one_or_none()
        
        if not float_obj:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Float {float_id} not found"}
            )
        
        return FloatDetailSchema.from_orm(float_obj)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting float {float_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/wmo/{wmo_id}", response_model=FloatDetailSchema)
async def get_float_by_wmo(
    wmo_id: str,
    include_profiles: bool = Query(True, description="Include profile data"),
    include_measurements: bool = Query(False, description="Include measurement data"),
    db: AsyncSession = Depends(get_db)
) -> FloatDetailSchema:
    """
    Get float information by WMO identifier.
    
    WMO ID is the standard identifier used in the Argo program.
    """
    try:
        # Build query
        query = select(Float).where(Float.wmo_id == wmo_id)
        
        if include_profiles:
            if include_measurements:
                query = query.options(
                    selectinload(Float.profiles).selectinload(Profile.measurements)
                )
            else:
                query = query.options(selectinload(Float.profiles))
        
        result = await db.execute(query)
        float_obj = result.scalar_one_or_none()
        
        if not float_obj:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Float with WMO ID {wmo_id} not found"}
            )
        
        return FloatDetailSchema.from_orm(float_obj)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting float by WMO {wmo_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.get("/nearby/{latitude}/{longitude}", response_model=List[FloatSummarySchema])
async def get_nearby_floats(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude"),
    radius_km: float = Query(100, ge=1, le=1000, description="Search radius in kilometers"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
) -> List[FloatSummarySchema]:
    """
    Find floats near a specific location.
    
    Returns floats that have profiles within the specified radius
    of the given coordinates, ordered by distance.
    """
    try:
        floats = await geospatial_service.find_nearby_floats(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit
        )
        
        return floats
        
    except Exception as e:
        logger.error(f"Error finding nearby floats: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Query Error", "message": str(e)}
        )


@router.post("/", response_model=FloatDetailSchema)
async def create_float(
    float_data: FloatCreate,
    db: AsyncSession = Depends(get_db)
) -> FloatDetailSchema:
    """
    Create a new float record.
    
    This endpoint is typically used for manual float registration
    or when ingesting data from external sources.
    """
    try:
        # Check if float with WMO ID already exists
        existing_query = select(Float).where(Float.wmo_id == float_data.wmo_id)
        existing_result = await db.execute(existing_query)
        existing_float = existing_result.scalar_one_or_none()
        
        if existing_float:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Conflict", 
                    "message": f"Float with WMO ID {float_data.wmo_id} already exists"
                }
            )
        
        # Create new float
        float_obj = Float(**float_data.dict())
        db.add(float_obj)
        await db.commit()
        await db.refresh(float_obj)
        
        logger.info(f"Created new float: {float_obj.wmo_id}")
        return FloatDetailSchema.from_orm(float_obj)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating float: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"error": "Database Error", "message": str(e)}
        )


@router.post("/{float_id}/ingest")
async def ingest_float_data(
    float_id: int,
    background_tasks: BackgroundTasks,
    force_update: bool = Query(False, description="Force update existing data"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Trigger data ingestion for a specific float.
    
    This will download and process the latest data from Argo servers
    for the specified float. The process runs in the background.
    """
    try:
        # Get float
        result = await db.execute(select(Float).where(Float.id == float_id))
        float_obj = result.scalar_one_or_none()
        
        if not float_obj:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Float {float_id} not found"}
            )
        
        # Add ingestion task to background
        background_tasks.add_task(
            ingestion_service.ingest_float_data,
            float_obj.wmo_id,
            force_update
        )
        
        return {
            "message": f"Data ingestion started for float {float_obj.wmo_id}",
            "float_id": float_id,
            "wmo_id": float_obj.wmo_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting ingestion for float {float_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Ingestion Error", "message": str(e)}
        )


@router.get("/{float_id}/statistics")
async def get_float_statistics(
    float_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get statistical summary for a float's data.
    
    Returns statistics about:
    - Profile count and temporal coverage
    - Measurement counts by variable
    - Depth range and spatial coverage
    - Data quality metrics
    """
    try:
        # Get float with profiles and measurements
        query = select(Float).where(Float.id == float_id).options(
            selectinload(Float.profiles).selectinload(Profile.measurements)
        )
        
        result = await db.execute(query)
        float_obj = result.scalar_one_or_none()
        
        if not float_obj:
            raise HTTPException(
                status_code=404,
                detail={"error": "Not Found", "message": f"Float {float_id} not found"}
            )
        
        # Calculate statistics
        stats = {
            "float_id": float_id,
            "wmo_id": float_obj.wmo_id,
            "profile_count": len(float_obj.profiles),
            "total_measurements": 0,
            "temporal_coverage": None,
            "spatial_coverage": None,
            "depth_range": None,
            "variable_counts": {},
            "data_quality": {}
        }
        
        if float_obj.profiles:
            # Temporal coverage
            timestamps = [p.timestamp for p in float_obj.profiles]
            stats["temporal_coverage"] = {
                "start_date": min(timestamps),
                "end_date": max(timestamps),
                "duration_days": (max(timestamps) - min(timestamps)).days
            }
            
            # Spatial coverage
            positions = [(p.latitude, p.longitude) for p in float_obj.profiles]
            lats, lons = zip(*positions)
            stats["spatial_coverage"] = {
                "min_latitude": min(lats),
                "max_latitude": max(lats),
                "min_longitude": min(lons),
                "max_longitude": max(lons)
            }
            
            # Measurement statistics
            all_measurements = []
            for profile in float_obj.profiles:
                all_measurements.extend(profile.measurements)
            
            stats["total_measurements"] = len(all_measurements)
            
            if all_measurements:
                # Depth range
                pressures = [m.pressure for m in all_measurements if m.pressure]
                if pressures:
                    stats["depth_range"] = {
                        "min_pressure": min(pressures),
                        "max_pressure": max(pressures)
                    }
                
                # Variable counts
                for var in ["temperature", "salinity", "dissolved_oxygen", "ph"]:
                    count = sum(1 for m in all_measurements if getattr(m, var) is not None)
                    if count > 0:
                        stats["variable_counts"][var] = count
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics for float {float_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Statistics Error", "message": str(e)}
        )
