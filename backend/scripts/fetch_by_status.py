"""
Fetch floats with specific status (inactive or maintenance) from Argo FTP.
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
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Float, Profile, Measurement


def get_floats_by_status(ftp_server, status='inactive', count=6):
    """
    Get float IDs with specific status from the Argo metadata index.
    Status can be: 'INACTIVE', 'CLOSED', etc.
    """
    print(f"Fetching list of {status} floats...")
    index_file_path = '/ifremer/argo/ar_index_global_meta.txt.gz'
    
    try:
        ftp = ftplib.FTP(ftp_server)
        ftp.login()
        in_memory_file = io.BytesIO()
        ftp.retrbinary(f'RETR {index_file_path}', in_memory_file.write)
        in_memory_file.seek(0)
        
        with gzip.open(in_memory_file, 'rt') as f:
            df = pd.read_csv(f, comment='#')
        
        # Filter by status if column exists
        if 'profiler_type' in df.columns:
            print(f"Available columns: {df.columns.tolist()}")
        
        # Extract float IDs and DACs
        df['float_id'] = df['file'].str.extract(r'/(\d+)/')
        df['dac'] = df['file'].str.split('/').str[0]
        
        # For now, get random floats and we'll check their actual status from the NetCDF files
        # The metadata index doesn't have a clear status field
        float_data = df[['float_id', 'dac']].dropna().drop_duplicates('float_id')
        
        # Select random floats to check
        selected = float_data.sample(min(count * 3, len(float_data)))  # Get more to filter
        
        print(f"Selected {len(selected)} floats to check status")
        ftp.quit()
        return selected.to_dict('records')
        
    except Exception as e:
        print(f"Error getting float list: {e}")
        return []


def download_latest_profile(ftp_server, float_id, dac):
    """
    Downloads the latest profile file for a float.
    """
    base_path = f'/ifremer/argo/dac/{dac}/{float_id}/profiles/'
    
    try:
        ftp = ftplib.FTP(ftp_server)
        ftp.login()
        ftp.cwd(base_path)
        
        # List files
        filenames = ftp.nlst()
        
        # Filter for NetCDF profile files
        nc_files = sorted([f for f in filenames if f.endswith('.nc') and f.startswith(('R', 'D'))])
        
        if not nc_files:
            ftp.quit()
            return None, None
        
        # Get the latest file
        latest_file_name = nc_files[-1]
        
        # Download to temp file
        tmp_file = tempfile.NamedTemporaryFile(suffix='.nc', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        with open(tmp_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {latest_file_name}', local_file.write)
        
        ftp.quit()
        
        # Check status from NetCDF
        ds = xr.open_dataset(tmp_path)
        status = 'active'  # Default
        
        # Try to determine status from attributes or data
        # If last profile is very old, consider it inactive
        if 'JULD' in ds.variables:
            try:
                last_juld = float(ds['JULD'].values[-1])
                if not pd.isna(last_juld) and 0 < last_juld < 100000:
                    last_date = datetime(1950, 1, 1) + timedelta(days=last_juld)
                    days_since_last = (datetime.utcnow() - last_date).days
                    
                    if days_since_last > 365:  # No data for over a year
                        status = 'inactive'
                    elif days_since_last > 180:  # No data for 6 months
                        status = 'maintenance'
            except:
                pass
        
        ds.close()
        return tmp_path, status
        
    except Exception as e:
        return None, None


async def ingest_float_file(file_path, wmo_id, status):
    """
    Ingest a float NetCDF file into the database with specific status.
    """
    try:
        ds = xr.open_dataset(file_path)
        
        async with AsyncSessionLocal() as session:
            try:
                # Create float with specified status
                float_obj = Float(
                    wmo_id=str(wmo_id),
                    platform_type=str(ds.attrs.get('platform_type', 'APEX'))[:100],
                    institution=str(ds.attrs.get('institution', 'Unknown'))[:200],
                    project_name=str(ds.attrs.get('project_name', 'Argo'))[:200],
                    status=status,  # Use the determined status
                    last_update=datetime.utcnow()
                )
                session.add(float_obj)
                await session.flush()
                print(f"  Created float in DB: ID={float_obj.id}, Status={status}")
                
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
    Main function to fetch floats with specific statuses.
    """
    ftp_server = 'ftp.ifremer.fr'
    
    print("=" * 60)
    print("Fetching Inactive and Maintenance Floats from Argo FTP")
    print("=" * 60)
    
    # Get candidate floats
    float_candidates = get_floats_by_status(ftp_server, count=20)
    
    if not float_candidates:
        print("Failed to get float candidates")
        return
    
    inactive_count = 0
    maintenance_count = 0
    inactive_target = 6
    maintenance_target = 6
    
    for idx, float_data in enumerate(float_candidates, 1):
        if inactive_count >= inactive_target and maintenance_count >= maintenance_target:
            break
        
        float_id = float_data['float_id']
        dac = float_data['dac']
        
        print(f"\n[{idx}] Checking float {float_id}")
        print("-" * 40)
        
        # Download file and check status
        file_path, status = download_latest_profile(ftp_server, float_id, dac)
        if not file_path:
            print(f"  Could not download")
            continue
        
        print(f"  Determined status: {status}")
        
        # Only ingest if we need this status
        should_ingest = False
        if status == 'inactive' and inactive_count < inactive_target:
            should_ingest = True
            inactive_count += 1
        elif status == 'maintenance' and maintenance_count < maintenance_target:
            should_ingest = True
            maintenance_count += 1
        
        if should_ingest:
            print(f"  Ingesting into database...")
            success = await ingest_float_file(file_path, float_id, status)
        else:
            print(f"  Skipping (already have enough {status} floats)")
        
        # Cleanup
        try:
            os.unlink(file_path)
        except:
            pass
    
    print("\n" + "=" * 60)
    print(f"SUCCESS: Ingested {inactive_count} inactive and {maintenance_count} maintenance floats")
    print("=" * 60)
    print("\nVerify by running:")
    print("  curl http://localhost:8000/api/v1/floats/?status=inactive")
    print("  curl http://localhost:8000/api/v1/floats/?status=maintenance")
    print("\nOr refresh your browser at http://localhost:8081")


if __name__ == "__main__":
    asyncio.run(main())
