#!/usr/bin/env python3
"""
Production-ready FTP ingestion script for Argo float data.
Connects to ftp.ifremer.fr, downloads NetCDF files, and ingests into PostgreSQL.
"""

import asyncio
import ftplib
import os
import sys
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
import xarray as xr
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import aiofiles

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal, init_db
from app.models import Float, Profile, Measurement
from app.config import settings
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ftp_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ArgoFTPIngestion:
    """Argo float data ingestion from FTP server."""
    
    def __init__(self):
        self.ftp_host = settings.FTP_HOST
        self.ftp_path = settings.FTP_PATH
        self.temp_dir = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processed_files = 0
        self.errors = []
        
    async def run_ingestion(self, max_files: int = 100) -> Dict[str, int]:
        """
        Main ingestion process.
        
        Args:
            max_files: Maximum number of files to process
            
        Returns:
            Dict with ingestion statistics
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting Argo FTP ingestion from {self.ftp_host}{self.ftp_path}")
        
        try:
            # Initialize database
            await init_db()
            
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="argo_ingestion_")
            logger.info(f"Using temporary directory: {self.temp_dir}")
            
            # Get list of NetCDF files from FTP
            nc_files = await self._list_ftp_files()
            logger.info(f"Found {len(nc_files)} NetCDF files on FTP server")
            
            if not nc_files:
                logger.warning("No NetCDF files found on FTP server")
                return {"processed": 0, "errors": 0}
            
            # Limit files for processing
            files_to_process = nc_files[:max_files]
            logger.info(f"Processing {len(files_to_process)} files")
            
            # Filter files that need processing
            new_files = await self._filter_new_files(files_to_process)
            logger.info(f"Found {len(new_files)} new files to process")
            
            # Process files in batches
            batch_size = 10
            for i in range(0, len(new_files), batch_size):
                batch = new_files[i:i + batch_size]
                await self._process_file_batch(batch)
            
            # Calculate statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            stats = {
                "processed": self.processed_files,
                "errors": len(self.errors),
                "processing_time": processing_time
            }
            
            logger.info(f"Ingestion completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Fatal error in ingestion: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
            self.executor.shutdown(wait=True)
    
    async def _list_ftp_files(self) -> List[str]:
        """List NetCDF files from FTP server."""
        loop = asyncio.get_event_loop()
        
        def _ftp_list():
            try:
                ftp = ftplib.FTP(self.ftp_host)
                ftp.login()  # Anonymous login
                ftp.cwd(self.ftp_path)
                
                files = []
                
                def collect_files(line):
                    if line.endswith('.nc') and '_prof.nc' in line:
                        files.append(line)
                
                # List files recursively
                self._recursive_ftp_list(ftp, "", collect_files)
                ftp.quit()
                
                return files
                
            except Exception as e:
                logger.error(f"Error listing FTP files: {e}")
                return []
        
        return await loop.run_in_executor(self.executor, _ftp_list)
    
    def _recursive_ftp_list(self, ftp: ftplib.FTP, path: str, callback):
        """Recursively list FTP directory contents."""
        try:
            current_path = f"{self.ftp_path}/{path}".rstrip('/')
            ftp.cwd(current_path)
            
            items = []
            ftp.retrlines('LIST', items.append)
            
            for item in items:
                parts = item.split()
                if len(parts) < 9:
                    continue
                    
                filename = ' '.join(parts[8:])
                is_directory = item.startswith('d')
                
                if is_directory and not filename.startswith('.'):
                    # Recursively process subdirectories
                    subpath = f"{path}/{filename}".strip('/')
                    self._recursive_ftp_list(ftp, subpath, callback)
                elif filename.endswith('.nc'):
                    full_path = f"{path}/{filename}".strip('/')
                    callback(full_path)
                    
        except Exception as e:
            logger.warning(f"Error listing directory {path}: {e}")
    
    async def _filter_new_files(self, files: List[str]) -> List[str]:
        """Filter files that need to be processed."""
        async with AsyncSessionLocal() as session:
            try:
                # Get existing WMO IDs from database
                result = await session.execute(select(Float.wmo_id))
                existing_wmo_ids = set(row[0] for row in result.fetchall())
                
                new_files = []
                for file_path in files:
                    wmo_id = self._extract_wmo_id(file_path)
                    if wmo_id and wmo_id not in existing_wmo_ids:
                        new_files.append(file_path)
                
                return new_files
                
            except Exception as e:
                logger.error(f"Error filtering files: {e}")
                return files  # Process all files if filtering fails
    
    def _extract_wmo_id(self, file_path: str) -> Optional[str]:
        """Extract WMO ID from file path."""
        try:
            # Argo file naming convention: {wmo_id}_prof.nc
            filename = os.path.basename(file_path)
            if '_prof.nc' in filename:
                return filename.split('_prof.nc')[0]
            return None
        except Exception:
            return None
    
    async def _process_file_batch(self, files: List[str]):
        """Process a batch of files concurrently."""
        tasks = [self._process_single_file(file_path) for file_path in files]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_file(self, file_path: str):
        """Process a single NetCDF file."""
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Download file
            local_file = await self._download_file(file_path)
            if not local_file:
                return
            
            # Parse NetCDF file
            dataset = await self._parse_netcdf(local_file)
            if dataset is None:
                return
            
            # Extract and save data
            await self._extract_and_save_data(dataset, file_path)
            
            self.processed_files += 1
            logger.info(f"Successfully processed: {file_path}")
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        finally:
            # Cleanup local file
            if 'local_file' in locals() and os.path.exists(local_file):
                os.remove(local_file)
    
    async def _download_file(self, file_path: str) -> Optional[str]:
        """Download file from FTP server."""
        loop = asyncio.get_event_loop()
        
        def _download():
            try:
                ftp = ftplib.FTP(self.ftp_host)
                ftp.login()
                
                local_filename = os.path.join(self.temp_dir, os.path.basename(file_path))
                
                with open(local_filename, 'wb') as f:
                    ftp.retrbinary(f'RETR {self.ftp_path}/{file_path}', f.write)
                
                ftp.quit()
                return local_filename
                
            except Exception as e:
                logger.error(f"Error downloading {file_path}: {e}")
                return None
        
        return await loop.run_in_executor(self.executor, _download)
    
    async def _parse_netcdf(self, file_path: str) -> Optional[xr.Dataset]:
        """Parse NetCDF file using xarray."""
        loop = asyncio.get_event_loop()
        
        def _parse():
            try:
                return xr.open_dataset(file_path)
            except Exception as e:
                logger.error(f"Error parsing NetCDF {file_path}: {e}")
                return None
        
        return await loop.run_in_executor(self.executor, _parse)
    
    async def _extract_and_save_data(self, dataset: xr.Dataset, file_path: str):
        """Extract data from dataset and save to database."""
        async with AsyncSessionLocal() as session:
            try:
                # Extract WMO ID
                wmo_id = self._extract_wmo_id(file_path)
                if not wmo_id:
                    logger.error(f"Could not extract WMO ID from {file_path}")
                    return
                
                # Create or get float
                float_obj = await self._upsert_float(session, wmo_id, dataset)
                
                # Extract profiles
                await self._extract_profiles(session, float_obj, dataset)
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error for {file_path}: {e}")
                raise
    
    async def _upsert_float(self, session, wmo_id: str, dataset: xr.Dataset) -> Float:
        """Create or update float record."""
        # Check if float exists
        result = await session.execute(
            select(Float).where(Float.wmo_id == wmo_id)
        )
        float_obj = result.scalar_one_or_none()
        
        if float_obj:
            # Update existing float
            float_obj.last_update = datetime.utcnow()
            return float_obj
        
        # Create new float
        float_data = {
            'wmo_id': wmo_id,
            'platform_type': self._get_attr(dataset, 'PLATFORM_TYPE'),
            'institution': self._get_attr(dataset, 'INSTITUTION'),
            'project_name': self._get_attr(dataset, 'PROJECT_NAME'),
            'pi_name': self._get_attr(dataset, 'PI_NAME'),
            'status': 'active',
            'last_update': datetime.utcnow()
        }
        
        float_obj = Float(**float_data)
        session.add(float_obj)
        await session.flush()
        
        return float_obj
    
    async def _extract_profiles(self, session, float_obj: Float, dataset: xr.Dataset):
        """Extract and save profiles from dataset."""
        try:
            n_prof = dataset.dims.get('N_PROF', 0)
            n_levels = dataset.dims.get('N_LEVELS', 0)
            
            for prof_idx in range(n_prof):
                await self._process_profile(session, float_obj, dataset, prof_idx, n_levels)
                
        except Exception as e:
            logger.error(f"Error extracting profiles: {e}")
            raise
    
    async def _process_profile(self, session, float_obj: Float, dataset: xr.Dataset, 
                             prof_idx: int, n_levels: int):
        """Process a single profile."""
        try:
            # Extract profile metadata
            cycle_number = int(dataset['CYCLE_NUMBER'].values[prof_idx])
            profile_id = f"{float_obj.wmo_id}_{cycle_number:03d}"
            
            # Convert Julian day to datetime
            juld = float(dataset['JULD'].values[prof_idx])
            timestamp = self._juld_to_datetime(juld)
            
            # Extract coordinates
            latitude = float(dataset['LATITUDE'].values[prof_idx])
            longitude = float(dataset['LONGITUDE'].values[prof_idx])
            
            # Skip invalid coordinates
            if np.isnan(latitude) or np.isnan(longitude):
                logger.warning(f"Invalid coordinates for profile {profile_id}")
                return
            
            # Create PostGIS geometry
            point = Point(longitude, latitude)
            location = from_shape(point, srid=4326)
            
            # Check if profile exists
            existing = await session.execute(
                select(Profile).where(Profile.profile_id == profile_id)
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Profile {profile_id} already exists, skipping")
                return
            
            # Create profile
            profile = Profile(
                float_id=float_obj.id,
                cycle_number=cycle_number,
                profile_id=profile_id,
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                location=location,
                direction=self._get_attr(dataset, 'DIRECTION', 'A'),
                data_mode=self._get_attr(dataset, 'DATA_MODE', 'R')
            )
            
            session.add(profile)
            await session.flush()
            
            # Extract measurements
            await self._extract_measurements(session, profile, dataset, prof_idx, n_levels)
            
        except Exception as e:
            logger.error(f"Error processing profile {prof_idx}: {e}")
            raise
    
    async def _extract_measurements(self, session, profile: Profile, dataset: xr.Dataset,
                                  prof_idx: int, n_levels: int):
        """Extract measurements for a profile."""
        measurements = []
        
        for level_idx in range(n_levels):
            try:
                # Extract pressure (required)
                pressure = self._get_measurement(dataset, 'PRES', prof_idx, level_idx)
                if pressure is None or np.isnan(pressure):
                    continue
                
                # Extract other variables
                temperature = self._get_measurement(dataset, 'TEMP', prof_idx, level_idx)
                salinity = self._get_measurement(dataset, 'PSAL', prof_idx, level_idx)
                
                measurement = Measurement(
                    profile_id=profile.id,
                    pressure=float(pressure),
                    depth=float(pressure * 0.98) if pressure else None,  # Approximate
                    temperature=float(temperature) if temperature and not np.isnan(temperature) else None,
                    salinity=float(salinity) if salinity and not np.isnan(salinity) else None,
                    measurement_order=level_idx
                )
                
                measurements.append(measurement)
                
            except Exception as e:
                logger.warning(f"Error extracting measurement {level_idx}: {e}")
                continue
        
        # Bulk insert measurements
        if measurements:
            session.add_all(measurements)
    
    def _get_attr(self, dataset: xr.Dataset, attr_name: str, default: str = None) -> Optional[str]:
        """Get attribute from dataset."""
        try:
            if attr_name in dataset.attrs:
                value = dataset.attrs[attr_name]
                return str(value).strip() if value else default
            return default
        except Exception:
            return default
    
    def _get_measurement(self, dataset: xr.Dataset, var_name: str, 
                        prof_idx: int, level_idx: int) -> Optional[float]:
        """Get measurement value from dataset."""
        try:
            if var_name in dataset.variables:
                value = dataset[var_name].values[prof_idx, level_idx]
                return float(value) if not np.isnan(value) else None
            return None
        except Exception:
            return None
    
    def _juld_to_datetime(self, juld: float) -> datetime:
        """Convert Julian day to datetime."""
        try:
            # Argo reference: 1950-01-01
            reference = datetime(1950, 1, 1)
            return reference + timedelta(days=float(juld))
        except Exception:
            return datetime.utcnow()


async def main():
    """Main execution function."""
    try:
        ingestion = ArgoFTPIngestion()
        
        # Run ingestion with limit for initial testing
        stats = await ingestion.run_ingestion(max_files=50)
        
        print(f"\nIngestion completed:")
        print(f"Files processed: {stats['processed']}")
        print(f"Errors: {stats['errors']}")
        print(f"Processing time: {stats['processing_time']:.2f} seconds")
        
        if ingestion.errors:
            print(f"\nErrors encountered:")
            for error in ingestion.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
