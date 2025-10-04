"""
CRUD operations for FloatChat backend.
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload, joinedload

from app.models import Float, Profile, Measurement

logger = logging.getLogger(__name__)


async def get_float_data_by_wmo_id(db: AsyncSession, wmo_id: str) -> Optional[Float]:
    """
    Fetch a Float object with all related Profiles and Measurements by WMO ID.
    
    Uses eager loading to avoid N+1 queries and fetch all related data in a single query.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        
    Returns:
        Float object with all relationships loaded, or None if not found
    """
    try:
        logger.info(f"Fetching float data for WMO ID: {wmo_id}")
        
        # Build query with eager loading of all relationships
        query = select(Float).where(Float.wmo_id == wmo_id).options(
            selectinload(Float.profiles).selectinload(Profile.measurements)
        )
        
        result = await db.execute(query)
        float_obj = result.scalar_one_or_none()
        
        if float_obj:
            logger.info(f"Found float {wmo_id} with {len(float_obj.profiles)} profiles")
            
            # Log measurement counts for debugging
            total_measurements = sum(len(profile.measurements) for profile in float_obj.profiles)
            logger.info(f"Float {wmo_id} has {total_measurements} total measurements")
        else:
            logger.warning(f"Float with WMO ID {wmo_id} not found")
        
        return float_obj
        
    except Exception as e:
        logger.error(f"Error fetching float data for WMO ID {wmo_id}: {e}")
        raise


async def get_latest_float_location(db: AsyncSession, wmo_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent location of a float by WMO ID.
    
    Returns the WMO ID and the latitude/longitude from the most recent profile.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        
    Returns:
        Dictionary with wmo_id, latitude, longitude, and timestamp, or None if not found
    """
    try:
        logger.info(f"Fetching latest location for WMO ID: {wmo_id}")
        
        # Query for the most recent profile of the specified float
        query = (
            select(Float.wmo_id, Profile.latitude, Profile.longitude, Profile.timestamp)
            .join(Profile, Float.id == Profile.float_id)
            .where(Float.wmo_id == wmo_id)
            .order_by(desc(Profile.timestamp))
            .limit(1)
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if row:
            location_data = {
                "wmo_id": row.wmo_id,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "timestamp": row.timestamp
            }
            logger.info(f"Latest location for {wmo_id}: {location_data['latitude']}, {location_data['longitude']}")
            return location_data
        else:
            logger.warning(f"No location data found for float {wmo_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching latest location for WMO ID {wmo_id}: {e}")
        raise


async def get_float_summary_by_wmo_id(db: AsyncSession, wmo_id: str) -> Optional[Dict[str, Any]]:
    """
    Get summary information for a float by WMO ID.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        
    Returns:
        Dictionary with float summary data, or None if not found
    """
    try:
        logger.info(f"Fetching float summary for WMO ID: {wmo_id}")
        
        # Query for float with profile count and latest profile date
        query = (
            select(
                Float.id,
                Float.wmo_id,
                Float.status,
                Float.platform_type,
                Float.institution,
                Float.deployment_latitude,
                Float.deployment_longitude,
                Float.last_update,
                func.count(Profile.id).label('profile_count'),
                func.max(Profile.timestamp).label('latest_profile_date')
            )
            .outerjoin(Profile, Float.id == Profile.float_id)
            .where(Float.wmo_id == wmo_id)
            .group_by(Float.id)
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if row:
            summary = {
                "id": row.id,
                "wmo_id": row.wmo_id,
                "status": row.status,
                "platform_type": row.platform_type,
                "institution": row.institution,
                "deployment_latitude": row.deployment_latitude,
                "deployment_longitude": row.deployment_longitude,
                "last_update": row.last_update,
                "profile_count": row.profile_count,
                "latest_profile_date": row.latest_profile_date
            }
            logger.info(f"Float {wmo_id} summary: {row.profile_count} profiles")
            return summary
        else:
            logger.warning(f"Float summary not found for WMO ID {wmo_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching float summary for WMO ID {wmo_id}: {e}")
        raise


async def get_float_profiles_by_wmo_id(
    db: AsyncSession, 
    wmo_id: str, 
    limit: int = 100,
    include_measurements: bool = False
) -> List[Profile]:
    """
    Get profiles for a float by WMO ID.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        limit: Maximum number of profiles to return
        include_measurements: Whether to include measurement data
        
    Returns:
        List of Profile objects
    """
    try:
        logger.info(f"Fetching profiles for WMO ID: {wmo_id} (limit: {limit})")
        
        # Build query with optional measurement loading
        query = (
            select(Profile)
            .join(Float, Profile.float_id == Float.id)
            .where(Float.wmo_id == wmo_id)
            .order_by(desc(Profile.timestamp))
            .limit(limit)
        )
        
        if include_measurements:
            query = query.options(selectinload(Profile.measurements))
        
        result = await db.execute(query)
        profiles = result.scalars().all()
        
        logger.info(f"Found {len(profiles)} profiles for float {wmo_id}")
        return profiles
        
    except Exception as e:
        logger.error(f"Error fetching profiles for WMO ID {wmo_id}: {e}")
        raise


async def get_measurement_statistics_by_wmo_id(db: AsyncSession, wmo_id: str) -> Dict[str, Any]:
    """
    Get measurement statistics for a float by WMO ID.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        
    Returns:
        Dictionary with measurement statistics
    """
    try:
        logger.info(f"Calculating measurement statistics for WMO ID: {wmo_id}")
        
        # Query for measurement statistics
        query = (
            select(
                func.count(Measurement.id).label('total_measurements'),
                func.min(Measurement.pressure).label('min_pressure'),
                func.max(Measurement.pressure).label('max_pressure'),
                func.avg(Measurement.temperature).label('avg_temperature'),
                func.min(Measurement.temperature).label('min_temperature'),
                func.max(Measurement.temperature).label('max_temperature'),
                func.avg(Measurement.salinity).label('avg_salinity'),
                func.min(Measurement.salinity).label('min_salinity'),
                func.max(Measurement.salinity).label('max_salinity'),
                func.count(Measurement.temperature).filter(Measurement.temperature.isnot(None)).label('temp_count'),
                func.count(Measurement.salinity).filter(Measurement.salinity.isnot(None)).label('sal_count')
            )
            .join(Profile, Measurement.profile_id == Profile.id)
            .join(Float, Profile.float_id == Float.id)
            .where(Float.wmo_id == wmo_id)
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if row and row.total_measurements > 0:
            stats = {
                "total_measurements": row.total_measurements,
                "pressure_range": {
                    "min": float(row.min_pressure) if row.min_pressure else None,
                    "max": float(row.max_pressure) if row.max_pressure else None
                },
                "temperature": {
                    "count": row.temp_count,
                    "avg": float(row.avg_temperature) if row.avg_temperature else None,
                    "min": float(row.min_temperature) if row.min_temperature else None,
                    "max": float(row.max_temperature) if row.max_temperature else None
                },
                "salinity": {
                    "count": row.sal_count,
                    "avg": float(row.avg_salinity) if row.avg_salinity else None,
                    "min": float(row.min_salinity) if row.min_salinity else None,
                    "max": float(row.max_salinity) if row.max_salinity else None
                }
            }
            logger.info(f"Statistics for {wmo_id}: {row.total_measurements} measurements")
            return stats
        else:
            logger.warning(f"No measurement statistics found for float {wmo_id}")
            return {
                "total_measurements": 0,
                "pressure_range": {"min": None, "max": None},
                "temperature": {"count": 0, "avg": None, "min": None, "max": None},
                "salinity": {"count": 0, "avg": None, "min": None, "max": None}
            }
            
    except Exception as e:
        logger.error(f"Error calculating statistics for WMO ID {wmo_id}: {e}")
        raise


async def check_float_exists(db: AsyncSession, wmo_id: str) -> bool:
    """
    Check if a float exists by WMO ID.
    
    Args:
        db: Database session
        wmo_id: WMO identifier of the float
        
    Returns:
        True if float exists, False otherwise
    """
    try:
        query = select(func.count(Float.id)).where(Float.wmo_id == wmo_id)
        result = await db.execute(query)
        count = result.scalar()
        
        exists = count > 0
        logger.info(f"Float {wmo_id} exists: {exists}")
        return exists
        
    except Exception as e:
        logger.error(f"Error checking if float {wmo_id} exists: {e}")
        raise


async def find_floats_by_params(db: AsyncSession, params) -> List[Dict[str, Any]]:
    """
    Find floats based on QueryParameters with PostGIS spatial filtering.
    
    Args:
        db: Database session
        params: QueryParameters object with search criteria
        
    Returns:
        List of FloatSummarySchema-compatible dictionaries
    """
    try:
        from geoalchemy2.functions import ST_Contains, ST_GeomFromText, ST_Intersects
        from sqlalchemy import and_, or_, desc
        
        logger.info(f"Searching floats with parameters: {params.dict() if hasattr(params, 'dict') else params}")
        
        # Base query with latest profile information
        subquery = (
            select(
                Profile.float_id,
                Profile.latitude,
                Profile.longitude,
                Profile.timestamp,
                func.row_number().over(
                    partition_by=Profile.float_id,
                    order_by=desc(Profile.timestamp)
                ).label('rn')
            )
            .subquery()
        )
        
        latest_profiles = select(subquery).where(subquery.c.rn == 1).subquery()
        
        # Main query joining floats with their latest profiles
        query = (
            select(
                Float.id,
                Float.wmo_id,
                Float.status,
                Float.platform_type,
                Float.institution,
                Float.last_update,
                latest_profiles.c.latitude,
                latest_profiles.c.longitude,
                latest_profiles.c.timestamp.label('latest_profile_date'),
                func.count(Profile.id).label('profile_count')
            )
            .outerjoin(latest_profiles, Float.id == latest_profiles.c.float_id)
            .outerjoin(Profile, Float.id == Profile.float_id)
            .group_by(
                Float.id,
                Float.wmo_id,
                Float.status,
                Float.platform_type,
                Float.institution,
                Float.last_update,
                latest_profiles.c.latitude,
                latest_profiles.c.longitude,
                latest_profiles.c.timestamp
            )
        )
        
        # Apply spatial filters
        if hasattr(params, 'bbox') and params.bbox:
            min_lon, min_lat, max_lon, max_lat = params.bbox
            
            # Create bounding box geometry
            bbox_wkt = f'POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))'
            bbox_geom = ST_GeomFromText(bbox_wkt, 4326)
            
            # Filter profiles within bounding box
            spatial_filter = (
                select(Profile.float_id)
                .where(ST_Intersects(Profile.location, bbox_geom))
                .distinct()
            )
            
            query = query.where(Float.id.in_(spatial_filter))
            logger.info(f"Applied bbox filter: {params.bbox}")
        
        # Apply temporal filters
        temporal_filters = []
        if hasattr(params, 'start_date') and params.start_date:
            temporal_filters.append(Profile.timestamp >= params.start_date)
        if hasattr(params, 'end_date') and params.end_date:
            temporal_filters.append(Profile.timestamp <= params.end_date)
        
        if temporal_filters:
            temporal_subquery = (
                select(Profile.float_id)
                .where(and_(*temporal_filters))
                .distinct()
            )
            query = query.where(Float.id.in_(temporal_subquery))
            logger.info(f"Applied temporal filters: {params.start_date} to {params.end_date}")
        
        # Apply variable filters (check if floats have measurements for requested variables)
        if hasattr(params, 'variables') and params.variables:
            variable_filters = []
            for variable in params.variables:
                if hasattr(Measurement, variable):
                    column = getattr(Measurement, variable)
                    variable_filters.append(column.isnot(None))
            
            if variable_filters:
                variable_subquery = (
                    select(Profile.float_id)
                    .join(Measurement, Profile.id == Measurement.profile_id)
                    .where(or_(*variable_filters))
                    .distinct()
                )
                query = query.where(Float.id.in_(variable_subquery))
                logger.info(f"Applied variable filters: {params.variables}")
        
        # Apply text search
        if hasattr(params, 'general_search_term') and params.general_search_term:
            search_term = f"%{params.general_search_term}%"
            text_filters = [
                Float.wmo_id.ilike(search_term),
                Float.institution.ilike(search_term),
                Float.project_name.ilike(search_term),
                Float.platform_type.ilike(search_term)
            ]
            query = query.where(or_(*text_filters))
            logger.info(f"Applied text search: {params.general_search_term}")
        
        # Execute query with limit
        query = query.limit(100)  # Limit results for performance
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Convert to FloatSummarySchema format
        floats = []
        for row in rows:
            float_summary = {
                "id": row.id,
                "wmo_id": row.wmo_id,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "status": row.status,
                "last_update": row.last_update,
                "profile_count": row.profile_count,
                "latest_profile_date": row.latest_profile_date
            }
            floats.append(float_summary)
        
        logger.info(f"Found {len(floats)} floats matching criteria")
        return floats
        
    except Exception as e:
        logger.error(f"Error finding floats by parameters: {e}")
        raise


async def get_recent_measurements_for_anomaly_detection(
    db: AsyncSession, 
    float_ids: List[int], 
    variables: List[str],
    days_back: int = 30
) -> Dict[str, List[float]]:
    """
    Get recent measurements for anomaly detection.
    
    Args:
        db: Database session
        float_ids: List of float IDs to check
        variables: Variables to analyze (temperature, salinity, etc.)
        days_back: Number of days to look back for baseline
        
    Returns:
        Dictionary with variable names as keys and lists of values
    """
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Build query for recent measurements
        query = (
            select(Measurement)
            .join(Profile, Measurement.profile_id == Profile.id)
            .join(Float, Profile.float_id == Float.id)
            .where(
                and_(
                    Profile.timestamp >= cutoff_date,
                    Float.id.in_(float_ids) if float_ids else True
                )
            )
            .limit(1000)  # Limit for performance
        )
        
        result = await db.execute(query)
        measurements = result.scalars().all()
        
        # Extract values for each variable
        variable_data = {}
        for variable in variables:
            if hasattr(Measurement, variable):
                values = []
                for measurement in measurements:
                    value = getattr(measurement, variable)
                    if value is not None:
                        values.append(float(value))
                variable_data[variable] = values
        
        logger.info(f"Retrieved {len(measurements)} recent measurements for anomaly detection")
        return variable_data
        
    except Exception as e:
        logger.error(f"Error getting recent measurements: {e}")
        return {}


async def get_latest_measurements_for_floats(
    db: AsyncSession, 
    float_ids: List[int], 
    variables: List[str]
) -> Dict[int, Dict[str, float]]:
    """
    Get latest measurements for specific floats.
    
    Args:
        db: Database session
        float_ids: List of float IDs
        variables: Variables to retrieve
        
    Returns:
        Dictionary mapping float_id to variable values
    """
    try:
        # Subquery for latest profile per float
        latest_profile_subquery = (
            select(
                Profile.float_id,
                func.max(Profile.timestamp).label('max_timestamp')
            )
            .where(Profile.float_id.in_(float_ids))
            .group_by(Profile.float_id)
            .subquery()
        )
        
        # Query for latest measurements
        query = (
            select(
                Float.id.label('float_id'),
                Measurement.temperature,
                Measurement.salinity,
                Measurement.pressure,
                Measurement.dissolved_oxygen,
                Measurement.ph
            )
            .join(Profile, Float.id == Profile.float_id)
            .join(Measurement, Profile.id == Measurement.profile_id)
            .join(
                latest_profile_subquery,
                and_(
                    Profile.float_id == latest_profile_subquery.c.float_id,
                    Profile.timestamp == latest_profile_subquery.c.max_timestamp
                )
            )
            .where(Float.id.in_(float_ids))
            .order_by(Measurement.pressure.desc())  # Get surface measurements first
        )
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Group by float_id and get first (surface) measurement
        float_measurements = {}
        for row in rows:
            if row.float_id not in float_measurements:
                measurements = {}
                for variable in variables:
                    if hasattr(row, variable):
                        value = getattr(row, variable)
                        if value is not None:
                            measurements[variable] = float(value)
                float_measurements[row.float_id] = measurements
        
        logger.info(f"Retrieved latest measurements for {len(float_measurements)} floats")
        return float_measurements
        
    except Exception as e:
        logger.error(f"Error getting latest measurements for floats: {e}")
        return {}
