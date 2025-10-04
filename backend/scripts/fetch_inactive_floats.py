"""
Fetch actual inactive and maintenance floats from Argo FTP based on their last update date.
"""
import asyncio
import sys
from pathlib import Path
import ftplib
import io
import gzip
import pandas as pd
import xarray as xr
from datetime import datetime, timedelta
import tempfile
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Float, Profile, Measurement


def get_all_floats_with_dates(ftp_server):
    """
    Get all floats with their last update dates from the Argo index.
    """
    print(f"Fetching Argo float index with dates...")
    index_file_path = '/ifremer/argo/ar_index_global_prof.txt.gz'
    
    try:
        ftp = ftplib.FTP(ftp_server, timeout=60)
        ftp.login()
        print("Connected to FTP, downloading index (this may take a minute)...")
        
        in_memory_file = io.BytesIO()
        ftp.retrbinary(f'RETR {index_file_path}', in_memory_file.write)
        in_memory_file.seek(0)
        
        print("Parsing index file...")
        with gzip.open(in_memory_file, 'rt') as f:
            df = pd.read_csv(f, comment='#')
        
        print(f"Loaded {len(df)} profiles from index")
        
        # Extract float info
        df['float_id'] = df['file'].str.extract(r'/(\d+)/')
        df['dac'] = df['file'].str.split('/').str[0]
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d%H%M%S', errors='coerce')
        
        # Get the latest date for each float
        float_latest = df.groupby(['float_id', 'dac'])['date'].max().reset_index()
        float_latest['days_since_update'] = (datetime.utcnow() - float_latest['date']).dt.days
        
        print(f"Found {len(float_latest)} unique floats")
        
        ftp.quit()
        return float_latest
        
    except Exception as e:
        print(f"Error getting float list: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_latest_profile(ftp_server, float_id, dac):
    """
    Downloads the latest profile file for a float.
    """
    base_path = f'/ifremer/argo/dac/{dac}/{float_id}/profiles/'
    
    try:
        ftp = ftplib.FTP(ftp_server, timeout=30)
        ftp.login()
        ftp.cwd(base_path)
        
        filenames = ftp.nlst()
        nc_files = sorted([f for f in filenames if f.endswith('.nc') and f.startswith(('R', 'D'))])
        
        if not nc_files:
            ftp.quit()
            return None
        
        latest_file_name = nc_files[-1]
        
        tmp_file = tempfile.NamedTemporaryFile(suffix='.nc', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        with open(tmp_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {latest_file_name}', local_file.write)
        
        ftp.quit()
        return tmp_path
        
    except Exception as e:
        print(f"  Download error: {e}")
        return None


async def ingest_float_file(file_path, wmo_id, status):
    """
    Ingest a float NetCDF file into the database with specific status.
    """
    try:
        ds = xr.open_dataset(file_path)
        
        async with AsyncSessionLocal() as session:
            try:
                # Check if float already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(Float).where(Float.wmo_id == str(wmo_id))
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"  Float {wmo_id} already exists, skipping")
                    return False
                
                # Create float with determined status
                float_obj = Float(
                    wmo_id=str(wmo_id),
                    platform_type=str(ds.attrs.get('platform_type', 'APEX'))[:100],
                    institution=str(ds.attrs.get('institution', 'Unknown'))[:200],
                    project_name=str(ds.attrs.get('project_name', 'Argo'))[:200],
                    status=status,
                    last_update=datetime.utcnow()
                )
                session.add(float_obj)
                await session.flush()
                print(f"  Created float: ID={float_obj.id}, Status={status}")
                
                # Process first 2 profiles
                num_profiles = min(2, ds.sizes.get('N_PROF', 0))
                profiles_added = 0
                
                for prof_idx in range(num_profiles):
                    if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
                        lat = float(ds['LATITUDE'].values[prof_idx])
                        lon = float(ds['LONGITUDE'].values[prof_idx])
                        
                        # Skip invalid coordinates
                        if pd.isna(lat) or pd.isna(lon) or abs(lat) > 90 or abs(lon) > 180:
                            continue
                        
                        # Get timestamp
                        if 'JULD' in ds.variables:
                            try:
                                juld = float(ds['JULD'].values[prof_idx])
                                if not pd.isna(juld) and 0 < juld < 100000:
                                    timestamp = datetime(1950, 1, 1) + timedelta(days=juld)
                                else:
                                    timestamp = datetime.utcnow()
                            except (ValueError, OverflowError, TypeError):
                                timestamp = datetime.utcnow()
                        else:
                            timestamp = datetime.utcnow()
                        
                        profile = Profile(
                            float_id=float_obj.id,
                            cycle_number=prof_idx + 1,
                            profile_id=f"{wmo_id}_{prof_idx+1}",
                            timestamp=timestamp,
                            latitude=lat,
                            longitude=lon,
                            direction='A',
                            data_mode='R'
                        )
                        session.add(profile)
                        await session.flush()
                        
                        # Add measurements
                        if 'PRES' in ds.variables:
                            pres = ds['PRES'].values[prof_idx]
                            temp = ds['TEMP'].values[prof_idx] if 'TEMP' in ds.variables else None
                            psal = ds['PSAL'].values[prof_idx] if 'PSAL' in ds.variables else None
                            
                            measurements_added = 0
                            for i in range(min(10, len(pres))):
                                if not pd.isna(pres[i]) and pres[i] > 0:
                                    measurement = Measurement(
                                        profile_id=profile.id,
                                        pressure=float(pres[i]),
                                        depth=float(pres[i]) * 1.02,
                                        temperature=float(temp[i]) if temp is not None and not pd.isna(temp[i]) else None,
                                        salinity=float(psal[i]) if psal is not None and not pd.isna(psal[i]) else None,
                                        measurement_order=i
                                    )
                                    session.add(measurement)
                                    measurements_added += 1
                            
                            if measurements_added > 0:
                                profiles_added += 1
                
                await session.commit()
                print(f"  Ingested {profiles_added} profiles")
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"  Database error: {e}")
                return False
        
    except Exception as e:
        print(f"  Error processing file: {e}")
        return False
    finally:
        try:
            ds.close()
        except:
            pass


async def main():
    """
    Main function to fetch floats and categorize by actual status.
    """
    ftp_server = 'ftp.ifremer.fr'
    
    print("=" * 60)
    print("Fetching Floats and Categorizing by Last Update Date")
    print("=" * 60)
    
    # Get all floats with dates
    float_df = get_all_floats_with_dates(ftp_server)
    
    if float_df is None or float_df.empty:
        print("Failed to get float data")
        return
    
    # Categorize by days since last update
    # Inactive: > 365 days
    # Maintenance: 180-365 days
    # Active: < 180 days
    
    inactive_floats = float_df[float_df['days_since_update'] > 365].head(6)
    maintenance_floats = float_df[
        (float_df['days_since_update'] >= 180) & 
        (float_df['days_since_update'] <= 365)
    ].head(6)
    
    print(f"\nFound {len(inactive_floats)} inactive floats (>365 days old)")
    print(f"Found {len(maintenance_floats)} maintenance floats (180-365 days old)")
    
    inactive_count = 0
    maintenance_count = 0
    
    # Process inactive floats
    print("\n" + "=" * 60)
    print("Processing INACTIVE floats")
    print("=" * 60)
    for idx, row in inactive_floats.iterrows():
        float_id = row['float_id']
        dac = row['dac']
        days = row['days_since_update']
        
        print(f"\n[Inactive {inactive_count+1}/6] Float {float_id} (last update: {days} days ago)")
        print("-" * 40)
        
        file_path = download_latest_profile(ftp_server, float_id, dac)
        if file_path:
            success = await ingest_float_file(file_path, float_id, 'inactive')
            if success:
                inactive_count += 1
            try:
                os.unlink(file_path)
            except:
                pass
    
    # Process maintenance floats
    print("\n" + "=" * 60)
    print("Processing MAINTENANCE floats")
    print("=" * 60)
    for idx, row in maintenance_floats.iterrows():
        float_id = row['float_id']
        dac = row['dac']
        days = row['days_since_update']
        
        print(f"\n[Maintenance {maintenance_count+1}/6] Float {float_id} (last update: {days} days ago)")
        print("-" * 40)
        
        file_path = download_latest_profile(ftp_server, float_id, dac)
        if file_path:
            success = await ingest_float_file(file_path, float_id, 'maintenance')
            if success:
                maintenance_count += 1
            try:
                os.unlink(file_path)
            except:
                pass
    
    print("\n" + "=" * 60)
    print(f"SUCCESS: Ingested {inactive_count} inactive and {maintenance_count} maintenance floats")
    print("=" * 60)
    print("\nTotal floats by status:")
    print(f"  Active: 90")
    print(f"  Inactive: {6 + inactive_count}")
    print(f"  Maintenance: {6 + maintenance_count}")
    print("\nRefresh your browser at http://localhost:8081 to see the updated map!")


if __name__ == "__main__":
    asyncio.run(main())
