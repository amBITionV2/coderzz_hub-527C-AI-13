"""
Data ingestion service for Argo oceanographic float data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import ftplib
import os
import tempfile
from pathlib import Path
import xarray as xr
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.database import AsyncSessionLocal
from app.models import Float, Profile, Measurement
from app.schemas import FloatCreate, ProfileCreate, MeasurementCreate
from app.config import settings

logger = logging.getLogger(__name__)


class ArgoDataIngestionService:
    """Service for ingesting Argo float data from various sources."""
    
    def __init__(self):
        self.ftp_host = settings.FTP_HOST
        self.ftp_path = settings.FTP_PATH
        self.data_url = settings.ARGO_DATA_URL
    
    async def ingest_float_data(self, wmo_id: str, force_update: bool = False) -> Optional[Float]:
        """
        Ingest data for a specific float by WMO ID.
        
        Args:
            wmo_id: WMO identifier of the float
            force_update: Whether to force update existing data
            
        Returns:
            Float: The ingested float object or None if failed
        """
        try:
            logger.info(f"Starting ingestion for float {wmo_id}")
            
            async with AsyncSessionLocal() as session:
                # Check if float already exists
                existing_float = await self._get_float_by_wmo(session, wmo_id)
                
                if existing_float and not force_update:
                    logger.info(f"Float {wmo_id} already exists, skipping")
                    return existing_float
                
                # Download and parse float data
                float_data = await self._download_float_data(wmo_id)
                if not float_data:
                    logger.error(f"Failed to download data for float {wmo_id}")
                    return None
                
                # Create or update float
                if existing_float:
                    float_obj = await self._update_float(session, existing_float, float_data)
                else:
                    float_obj = await self._create_float(session, wmo_id, float_data)
                
                await session.commit()
                logger.info(f"Successfully ingested float {wmo_id}")
                return float_obj
                
        except Exception as e:
            logger.error(f"Error ingesting float {wmo_id}: {e}")
            return None
    
    async def ingest_recent_data(self, days: int = 7) -> Dict[str, Any]:
        """
        Ingest recent data from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict: Summary of ingestion results
        """
        start_time = datetime.utcnow()
        results = {
            'floats_processed': 0,
            'floats_created': 0,
            'floats_updated': 0,
            'profiles_created': 0,
            'errors': []
        }
        
        try:
            # Get list of recently updated floats
            recent_floats = await self._get_recent_float_list(days)
            
            for wmo_id in recent_floats:
                try:
                    float_obj = await self.ingest_float_data(wmo_id, force_update=True)
                    if float_obj:
                        results['floats_processed'] += 1
                        # Count profiles created in this session
                        # This would need to be tracked during ingestion
                    
                except Exception as e:
                    error_msg = f"Failed to process float {wmo_id}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Ingestion completed in {processing_time:.2f} seconds")
            results['processing_time'] = processing_time
            
        except Exception as e:
            logger.error(f"Error during bulk ingestion: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def _download_float_data(self, wmo_id: str) -> Optional[xr.Dataset]:
        """
        Download float data from Argo FTP server.
        
        Args:
            wmo_id: WMO identifier
            
        Returns:
            xr.Dataset: Parsed float data or None if failed
        """
        try:
            # Create temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                # Construct file path based on WMO ID
                # Argo files are typically organized by DAC and float ID
                file_pattern = f"*{wmo_id}*.nc"
                
                # Download file via FTP
                local_file = await self._download_via_ftp(wmo_id, temp_dir)
                if not local_file:
                    return None
                
                # Parse NetCDF file
                dataset = xr.open_dataset(local_file)
                return dataset
                
        except Exception as e:
            logger.error(f"Error downloading float data for {wmo_id}: {e}")
            return None
    
    async def _download_via_ftp(self, wmo_id: str, temp_dir: str) -> Optional[str]:
        """
        Download float file via FTP.
        
        Args:
            wmo_id: WMO identifier
            temp_dir: Temporary directory for download
            
        Returns:
            str: Path to downloaded file or None if failed
        """
        try:
            # This is a simplified version - real implementation would need
            # to navigate the Argo directory structure
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login()
            
            # Navigate to appropriate directory
            # Real Argo structure: /ifremer/argo/dac/{dac}/{float_id}/
            # For now, we'll simulate this
            
            # Find the appropriate file
            filename = f"{wmo_id}_prof.nc"
            local_path = os.path.join(temp_dir, filename)
            
            # Download file
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            
            ftp.quit()
            return local_path
            
        except Exception as e:
            logger.error(f"FTP download failed for {wmo_id}: {e}")
            return None
    
    async def _get_recent_float_list(self, days: int) -> List[str]:
        """
        Get list of recently updated floats.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List[str]: List of WMO IDs
        """
        # This would typically query the Argo index or use FTP directory listing
        # For now, return a sample list
        return ["1901393", "1901394", "1901395"]  # Sample WMO IDs
    
    async def _get_float_by_wmo(self, session: AsyncSession, wmo_id: str) -> Optional[Float]:
        """Get float by WMO ID."""
        result = await session.execute(
            select(Float).where(Float.wmo_id == wmo_id)
        )
        return result.scalar_one_or_none()
    
    async def _create_float(self, session: AsyncSession, wmo_id: str, data: xr.Dataset) -> Float:
        """
        Create new float from dataset.
        
        Args:
            session: Database session
            wmo_id: WMO identifier
            data: Parsed float dataset
            
        Returns:
            Float: Created float object
        """
        # Extract float metadata from dataset
        float_data = FloatCreate(
            wmo_id=wmo_id,
            platform_type=self._extract_attribute(data, 'PLATFORM_TYPE'),
            institution=self._extract_attribute(data, 'INSTITUTION'),
            project_name=self._extract_attribute(data, 'PROJECT_NAME'),
            pi_name=self._extract_attribute(data, 'PI_NAME'),
            deployment_date=self._extract_date(data, 'REFERENCE_DATE_TIME'),
            status='active'
        )
        
        # Create float
        float_obj = Float(**float_data.dict())
        session.add(float_obj)
        await session.flush()  # Get the ID
        
        # Create profiles
        await self._create_profiles_from_dataset(session, float_obj, data)
        
        return float_obj
    
    async def _update_float(self, session: AsyncSession, float_obj: Float, data: xr.Dataset) -> Float:
        """
        Update existing float with new data.
        
        Args:
            session: Database session
            float_obj: Existing float object
            data: New dataset
            
        Returns:
            Float: Updated float object
        """
        # Update float metadata
        float_obj.last_update = datetime.utcnow()
        
        # Add new profiles
        await self._create_profiles_from_dataset(session, float_obj, data)
        
        return float_obj
    
    async def _create_profiles_from_dataset(
        self, 
        session: AsyncSession, 
        float_obj: Float, 
        data: xr.Dataset
    ) -> None:
        """
        Create profiles from dataset.
        
        Args:
            session: Database session
            float_obj: Float object
            data: Dataset containing profile data
        """
        try:
            # Extract profile dimensions
            n_prof = data.dims.get('N_PROF', 0)
            n_levels = data.dims.get('N_LEVELS', 0)
            
            for prof_idx in range(n_prof):
                # Extract profile metadata
                cycle_number = int(data['CYCLE_NUMBER'].values[prof_idx])
                profile_id = f"{float_obj.wmo_id}_{cycle_number}"
                
                # Extract timestamp
                juld = data['JULD'].values[prof_idx]
                timestamp = self._convert_juld_to_datetime(juld)
                
                # Extract position
                latitude = float(data['LATITUDE'].values[prof_idx])
                longitude = float(data['LONGITUDE'].values[prof_idx])
                
                # Create geometry point
                point = Point(longitude, latitude)
                location = from_shape(point, srid=4326)
                
                # Create profile
                profile = Profile(
                    float_id=float_obj.id,
                    cycle_number=cycle_number,
                    profile_id=profile_id,
                    timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                    location=location,
                    direction='A',  # Default to ascending
                    data_mode='R'   # Default to real-time
                )
                
                session.add(profile)
                await session.flush()  # Get profile ID
                
                # Create measurements for this profile
                await self._create_measurements_from_profile(
                    session, profile, data, prof_idx, n_levels
                )
                
        except Exception as e:
            logger.error(f"Error creating profiles: {e}")
            raise
    
    async def _create_measurements_from_profile(
        self,
        session: AsyncSession,
        profile: Profile,
        data: xr.Dataset,
        prof_idx: int,
        n_levels: int
    ) -> None:
        """
        Create measurements for a profile.
        
        Args:
            session: Database session
            profile: Profile object
            data: Dataset
            prof_idx: Profile index
            n_levels: Number of measurement levels
        """
        try:
            for level_idx in range(n_levels):
                # Extract measurement data
                pressure = self._extract_measurement_value(data, 'PRES', prof_idx, level_idx)
                temperature = self._extract_measurement_value(data, 'TEMP', prof_idx, level_idx)
                salinity = self._extract_measurement_value(data, 'PSAL', prof_idx, level_idx)
                
                # Skip if no valid pressure (required field)
                if pressure is None or np.isnan(pressure):
                    continue
                
                # Create measurement
                measurement = Measurement(
                    profile_id=profile.id,
                    pressure=float(pressure),
                    temperature=float(temperature) if temperature is not None and not np.isnan(temperature) else None,
                    salinity=float(salinity) if salinity is not None and not np.isnan(salinity) else None,
                    measurement_order=level_idx
                )
                
                session.add(measurement)
                
        except Exception as e:
            logger.error(f"Error creating measurements: {e}")
            raise
    
    def _extract_attribute(self, data: xr.Dataset, attr_name: str) -> Optional[str]:
        """Extract string attribute from dataset."""
        try:
            if attr_name in data.attrs:
                return str(data.attrs[attr_name])
            return None
        except Exception:
            return None
    
    def _extract_date(self, data: xr.Dataset, var_name: str) -> Optional[datetime]:
        """Extract date from dataset variable."""
        try:
            if var_name in data.variables:
                date_str = str(data[var_name].values)
                # Parse Argo date format (YYYYMMDDHHMISS)
                return datetime.strptime(date_str[:14], '%Y%m%d%H%M%S')
            return None
        except Exception:
            return None
    
    def _convert_juld_to_datetime(self, juld: float) -> datetime:
        """
        Convert Julian day to datetime.
        
        Args:
            juld: Julian day number
            
        Returns:
            datetime: Converted datetime
        """
        try:
            # Argo reference date is 1950-01-01
            reference_date = datetime(1950, 1, 1)
            return reference_date + timedelta(days=float(juld))
        except Exception:
            return datetime.utcnow()
    
    def _extract_measurement_value(
        self, 
        data: xr.Dataset, 
        var_name: str, 
        prof_idx: int, 
        level_idx: int
    ) -> Optional[float]:
        """Extract measurement value from dataset."""
        try:
            if var_name in data.variables:
                value = data[var_name].values[prof_idx, level_idx]
                return float(value) if not np.isnan(value) else None
            return None
        except Exception:
            return None


# Global ingestion service instance
ingestion_service = ArgoDataIngestionService()
