"""
Geospatial query service for oceanographic data.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_DWithin, ST_GeomFromText, ST_Distance, ST_Contains
from geoalchemy2.shape import to_shape
from shapely.geometry import Point, Polygon

from app.models import Float, Profile, Measurement
from app.schemas import QueryParameters, FloatSummarySchema, ProfileSummary
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class GeospatialQueryService:
    """Service for geospatial queries on oceanographic data."""
    
    async def query_floats_by_parameters(
        self, 
        parameters: QueryParameters,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[FloatSummarySchema], Dict[str, Any]]:
        """
        Query floats based on structured parameters.
        
        Args:
            parameters: Query parameters
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (floats list, data summary)
        """
        async with AsyncSessionLocal() as session:
            # Build base query
            query = select(Float).options(
                selectinload(Float.profiles).selectinload(Profile.measurements)
            )
            
            # Apply spatial filters
            if parameters.bbox:
                query = self._apply_bbox_filter(query, parameters.bbox)
            elif parameters.location:
                query = await self._apply_location_filter(query, parameters.location)
            
            # Apply temporal filters
            if parameters.start_date or parameters.end_date:
                query = self._apply_temporal_filter(query, parameters.start_date, parameters.end_date)
            
            # Apply variable filters
            if parameters.variables:
                query = self._apply_variable_filter(query, parameters.variables)
            
            # Apply depth filters
            if parameters.depth_range:
                query = self._apply_depth_filter(query, parameters.depth_range)
            
            # Apply text search
            if parameters.general_search_term:
                query = self._apply_text_filter(query, parameters.general_search_term)
            
            # Execute query with pagination
            result = await session.execute(
                query.offset(offset).limit(limit)
            )
            floats = result.scalars().all()
            
            # Convert to summary schemas
            float_summaries = []
            for float_obj in floats:
                summary = await self._create_float_summary(float_obj)
                float_summaries.append(summary)
            
            # Generate data summary
            data_summary = await self._generate_data_summary(session, floats, parameters)
            
            return float_summaries, data_summary
    
    async def find_nearby_floats(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 100,
        limit: int = 50
    ) -> List[FloatSummarySchema]:
        """
        Find floats within a specified radius of a point.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers
            limit: Maximum number of results
            
        Returns:
            List of nearby floats
        """
        async with AsyncSessionLocal() as session:
            # Create point geometry
            center_point = ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
            
            # Query for nearby profiles (which link to floats)
            query = select(Profile).join(Float).where(
                ST_DWithin(Profile.location, center_point, radius_km * 1000)  # Convert km to meters
            ).order_by(
                ST_Distance(Profile.location, center_point)
            ).limit(limit)
            
            result = await session.execute(query)
            profiles = result.scalars().all()
            
            # Get unique floats from profiles
            float_ids = list(set(profile.float_id for profile in profiles))
            
            # Fetch float details
            float_query = select(Float).where(Float.id.in_(float_ids))
            float_result = await session.execute(float_query)
            floats = float_result.scalars().all()
            
            # Convert to summaries
            summaries = []
            for float_obj in floats:
                summary = await self._create_float_summary(float_obj)
                summaries.append(summary)
            
            return summaries
    
    async def get_profiles_in_region(
        self,
        bbox: List[float],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[ProfileSummary]:
        """
        Get profiles within a bounding box and time range.
        
        Args:
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat]
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of profiles
            
        Returns:
            List of profile summaries
        """
        async with AsyncSessionLocal() as session:
            # Create bounding box polygon
            min_lon, min_lat, max_lon, max_lat = bbox
            bbox_wkt = f'POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))'
            bbox_geom = ST_GeomFromText(bbox_wkt, 4326)
            
            # Build query
            query = select(Profile).where(
                ST_Contains(bbox_geom, Profile.location)
            )
            
            # Apply temporal filters
            if start_date:
                query = query.where(Profile.timestamp >= start_date)
            if end_date:
                query = query.where(Profile.timestamp <= end_date)
            
            # Order by timestamp and limit
            query = query.order_by(Profile.timestamp.desc()).limit(limit)
            
            result = await session.execute(query)
            profiles = result.scalars().all()
            
            # Convert to summaries
            summaries = []
            for profile in profiles:
                # Count measurements
                measurement_count = await self._count_measurements(session, profile.id)
                
                summary = ProfileSummary(
                    id=profile.id,
                    cycle_number=profile.cycle_number,
                    timestamp=profile.timestamp,
                    latitude=profile.latitude,
                    longitude=profile.longitude,
                    measurement_count=measurement_count
                )
                summaries.append(summary)
            
            return summaries
    
    async def calculate_ocean_statistics(
        self,
        parameters: QueryParameters
    ) -> Dict[str, Any]:
        """
        Calculate statistical summaries for oceanographic variables.
        
        Args:
            parameters: Query parameters
            
        Returns:
            Dictionary of statistics
        """
        async with AsyncSessionLocal() as session:
            stats = {}
            
            # Build base measurement query
            query = select(Measurement).join(Profile).join(Float)
            
            # Apply filters
            if parameters.bbox:
                query = self._apply_measurement_bbox_filter(query, parameters.bbox)
            
            if parameters.start_date or parameters.end_date:
                query = self._apply_measurement_temporal_filter(
                    query, parameters.start_date, parameters.end_date
                )
            
            if parameters.depth_range:
                min_depth, max_depth = parameters.depth_range
                query = query.where(
                    and_(
                        Measurement.pressure >= min_depth * 1.02,  # Approximate depth to pressure conversion
                        Measurement.pressure <= max_depth * 1.02
                    )
                )
            
            # Calculate statistics for each variable
            variables = parameters.variables or ['temperature', 'salinity', 'pressure']
            
            for variable in variables:
                if hasattr(Measurement, variable):
                    column = getattr(Measurement, variable)
                    
                    # Calculate statistics
                    stat_query = select(
                        func.count(column).label('count'),
                        func.avg(column).label('mean'),
                        func.min(column).label('min'),
                        func.max(column).label('max'),
                        func.stddev(column).label('stddev')
                    ).select_from(query.subquery()).where(column.isnot(None))
                    
                    result = await session.execute(stat_query)
                    row = result.first()
                    
                    if row and row.count > 0:
                        stats[variable] = {
                            'count': row.count,
                            'mean': float(row.mean) if row.mean else None,
                            'min': float(row.min) if row.min else None,
                            'max': float(row.max) if row.max else None,
                            'stddev': float(row.stddev) if row.stddev else None
                        }
            
            return stats
    
    def _apply_bbox_filter(self, query, bbox: List[float]):
        """Apply bounding box filter to float query."""
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Create bounding box polygon
        bbox_wkt = f'POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))'
        bbox_geom = ST_GeomFromText(bbox_wkt, 4326)
        
        # Filter floats that have profiles within the bounding box
        return query.join(Profile).where(
            ST_Contains(bbox_geom, Profile.location)
        ).distinct()
    
    async def _apply_location_filter(self, query, location: str):
        """Apply location name filter to query."""
        # This would typically involve geocoding the location name
        # For now, we'll do simple keyword matching
        location_lower = location.lower()
        
        # Define some basic ocean regions
        region_bounds = {
            'pacific': [-180, -60, -70, 60],
            'atlantic': [-80, -60, 20, 70],
            'indian': [20, -60, 120, 30],
            'arctic': [-180, 60, 180, 90],
            'southern': [-180, -90, 180, -60]
        }
        
        for region, bbox in region_bounds.items():
            if region in location_lower:
                return self._apply_bbox_filter(query, bbox)
        
        # If no match, return original query
        return query
    
    def _apply_temporal_filter(self, query, start_date: Optional[datetime], end_date: Optional[datetime]):
        """Apply temporal filter to query."""
        # Filter based on profile timestamps
        query = query.join(Profile)
        
        if start_date:
            query = query.where(Profile.timestamp >= start_date)
        if end_date:
            query = query.where(Profile.timestamp <= end_date)
        
        return query.distinct()
    
    def _apply_variable_filter(self, query, variables: List[str]):
        """Apply variable availability filter."""
        # Filter floats that have measurements for the requested variables
        measurement_filters = []
        
        for variable in variables:
            if hasattr(Measurement, variable):
                column = getattr(Measurement, variable)
                measurement_filters.append(column.isnot(None))
        
        if measurement_filters:
            query = query.join(Profile).join(Measurement).where(
                or_(*measurement_filters)
            ).distinct()
        
        return query
    
    def _apply_depth_filter(self, query, depth_range: List[float]):
        """Apply depth range filter."""
        min_depth, max_depth = depth_range
        
        # Convert depth to pressure (approximate: 1 meter = 1.02 dbar)
        min_pressure = min_depth * 1.02
        max_pressure = max_depth * 1.02
        
        query = query.join(Profile).join(Measurement).where(
            and_(
                Measurement.pressure >= min_pressure,
                Measurement.pressure <= max_pressure
            )
        ).distinct()
        
        return query
    
    def _apply_text_filter(self, query, search_term: str):
        """Apply text search filter."""
        # Search in float metadata fields
        search_pattern = f'%{search_term}%'
        
        query = query.where(
            or_(
                Float.institution.ilike(search_pattern),
                Float.project_name.ilike(search_pattern),
                Float.pi_name.ilike(search_pattern),
                Float.platform_type.ilike(search_pattern)
            )
        )
        
        return query
    
    def _apply_measurement_bbox_filter(self, query, bbox: List[float]):
        """Apply bounding box filter to measurement query."""
        min_lon, min_lat, max_lon, max_lat = bbox
        bbox_wkt = f'POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))'
        bbox_geom = ST_GeomFromText(bbox_wkt, 4326)
        
        return query.where(ST_Contains(bbox_geom, Profile.location))
    
    def _apply_measurement_temporal_filter(
        self, 
        query, 
        start_date: Optional[datetime], 
        end_date: Optional[datetime]
    ):
        """Apply temporal filter to measurement query."""
        if start_date:
            query = query.where(Profile.timestamp >= start_date)
        if end_date:
            query = query.where(Profile.timestamp <= end_date)
        
        return query
    
    async def _create_float_summary(self, float_obj: Float) -> FloatSummarySchema:
        """Create float summary from float object."""
        import math
        
        # Get latest profile for position
        latest_profile = None
        if float_obj.profiles:
            latest_profile = max(float_obj.profiles, key=lambda p: p.timestamp)
        
        # Get latitude/longitude, handling NaN values
        lat = latest_profile.latitude if latest_profile else float_obj.deployment_latitude
        lon = latest_profile.longitude if latest_profile else float_obj.deployment_longitude
        
        # Replace NaN with None
        if lat is not None and (math.isnan(lat) or math.isinf(lat)):
            lat = None
        if lon is not None and (math.isnan(lon) or math.isinf(lon)):
            lon = None
        
        return FloatSummarySchema(
            id=float_obj.id,
            wmo_id=float_obj.wmo_id,
            latitude=lat,
            longitude=lon,
            status=float_obj.status,
            last_update=float_obj.last_update,
            profile_count=len(float_obj.profiles),
            latest_profile_date=latest_profile.timestamp if latest_profile else None
        )
    
    async def _count_measurements(self, session: AsyncSession, profile_id: int) -> int:
        """Count measurements for a profile."""
        result = await session.execute(
            select(func.count(Measurement.id)).where(Measurement.profile_id == profile_id)
        )
        return result.scalar() or 0
    
    async def _generate_data_summary(
        self, 
        session: AsyncSession, 
        floats: List[Float], 
        parameters: QueryParameters
    ) -> Dict[str, Any]:
        """Generate summary statistics for the query results."""
        summary = {
            'float_count': len(floats),
            'profile_count': sum(len(f.profiles) for f in floats),
            'measurement_count': 0,
            'date_range': None,
            'spatial_extent': None
        }
        
        if not floats:
            return summary
        
        # Calculate measurement count
        for float_obj in floats:
            for profile in float_obj.profiles:
                summary['measurement_count'] += len(profile.measurements)
        
        # Calculate date range
        all_dates = []
        for float_obj in floats:
            for profile in float_obj.profiles:
                all_dates.append(profile.timestamp)
        
        if all_dates:
            summary['date_range'] = {
                'start': min(all_dates),
                'end': max(all_dates)
            }
        
        # Calculate spatial extent
        all_positions = []
        for float_obj in floats:
            for profile in float_obj.profiles:
                all_positions.append((profile.longitude, profile.latitude))
        
        if all_positions:
            lons, lats = zip(*all_positions)
            summary['spatial_extent'] = {
                'min_longitude': min(lons),
                'max_longitude': max(lons),
                'min_latitude': min(lats),
                'max_latitude': max(lats)
            }
        
        # Add variable-specific statistics
        if parameters.variables:
            stats = await self.calculate_ocean_statistics(parameters)
            summary['variable_statistics'] = stats
        
        return summary


# Global geospatial service instance
geospatial_service = GeospatialQueryService()
