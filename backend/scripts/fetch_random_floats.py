"""
Fetch 3 random floats from Argo FTP and ingest into database.
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


def get_random_floats(ftp_server, count=3):
    """
    Get random float IDs from the Argo metadata index.
    """
    print(f"Fetching list of available floats...")
    index_file_path = '/ifremer/argo/ar_index_global_meta.txt.gz'
    
    try:
        ftp = ftplib.FTP(ftp_server)
        ftp.login()
        in_memory_file = io.BytesIO()
        ftp.retrbinary(f'RETR {index_file_path}', in_memory_file.write)
        in_memory_file.seek(0)
        
        with gzip.open(in_memory_file, 'rt') as f:
            df = pd.read_csv(f, comment='#')
        
        # Extract float IDs from file paths
        df['float_id'] = df['file'].str.extract(r'/(\d+)/')
        float_ids = df['float_id'].dropna().unique().tolist()
        
        # Select random floats
        selected = random.sample(float_ids, min(count, len(float_ids)))
        print(f"Selected {len(selected)} random floats: {selected}")
        
        ftp.quit()
        return selected
        
    except Exception as e:
        print(f"Error getting float list: {e}")
        return []


def get_dac_for_float(ftp_server, float_id):
    """
    Finds the correct DAC for a float by checking the master metadata index.
    """
    print(f"Looking up DAC for float {float_id}...")
    index_file_path = '/ifremer/argo/ar_index_global_meta.txt.gz'
    
    try:
        ftp = ftplib.FTP(ftp_server)
        ftp.login()
        in_memory_file = io.BytesIO()
        ftp.retrbinary(f'RETR {index_file_path}', in_memory_file.write)
        in_memory_file.seek(0)
        
        with gzip.open(in_memory_file, 'rt') as f:
            df = pd.read_csv(f, comment='#')
        
        float_row = df[df['file'].str.contains(f'/{float_id}/', na=False)]
        
        if not float_row.empty:
            dac_name = float_row.iloc[0]['file'].split('/')[0]
            print(f"  Found DAC: '{dac_name}'")
            ftp.quit()
            return dac_name
            
    except ftplib.all_errors as e:
        print(f"  FTP Error during DAC lookup: {e}")
    finally:
        if 'ftp' in locals() and ftp.sock:
            try:
                ftp.quit()
            except:
                pass
    
    print(f"  Could not determine DAC for float {float_id}.")
    return None


def download_latest_profile(ftp_server, float_id, dac):
    """
    Downloads the main profile file containing ALL profiles for a float.
    """
    # Try to get the main _prof.nc file which contains all profiles
    base_path = f'/ifremer/argo/dac/{dac}/{float_id}/'
    main_file = f'{float_id}_prof.nc'
    
    try:
        ftp = ftplib.FTP(ftp_server)
        ftp.login()
        ftp.cwd(base_path)
        
        # Check if main profile file exists
        filenames = ftp.nlst()
        
        if main_file not in filenames:
            print(f"  Main profile file not found")
            ftp.quit()
            return None
        
        print(f"  Downloading: {main_file} (contains all profiles)")
        
        # Download to temp file
        tmp_file = tempfile.NamedTemporaryFile(suffix='.nc', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        with open(tmp_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {main_file}', local_file.write)
        
        ftp.quit()
        print(f"  Downloaded successfully")
        return tmp_path
        
    except Exception as e:
        print(f"  Error downloading: {e}")
        return None


async def ingest_float_file(file_path, wmo_id):
    """
    Ingest a float NetCDF file into the database.
    """
    try:
        ds = xr.open_dataset(file_path)
        
        async with AsyncSessionLocal() as session:
            try:
                # Create float
                float_obj = Float(
                    wmo_id=str(wmo_id),
                    platform_type=str(ds.attrs.get('platform_type', 'APEX'))[:100],
                    institution=str(ds.attrs.get('institution', 'Unknown'))[:200],
                    project_name=str(ds.attrs.get('project_name', 'Argo'))[:200],
                    status='active',
                    last_update=datetime.utcnow()
                )
                session.add(float_obj)
                await session.flush()
                print(f"  Created float in DB: ID={float_obj.id}")
                
                # Process up to 30 profiles per float (for performance)
                num_profiles = min(30, ds.sizes.get('N_PROF', 0))
                profiles_added = 0
                
                for prof_idx in range(num_profiles):
                    if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
                        lat = float(ds['LATITUDE'].values[prof_idx])
                        lon = float(ds['LONGITUDE'].values[prof_idx])
                        
                        # Skip invalid coordinates
                        if abs(lat) > 90 or abs(lon) > 180:
                            continue
                        
                        # Get timestamp
                        if 'JULD' in ds.variables:
                            try:
                                juld = float(ds['JULD'].values[prof_idx])
                                if not pd.isna(juld) and 0 < juld < 100000:  # Sanity check
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
                            # Process ALL measurements, not just first 15
                            for i in range(len(pres)):
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
                print(f"  Ingested {profiles_added} profiles with measurements")
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
    Main function to fetch and ingest 100 random floats.
    """
    ftp_server = 'ftp.ifremer.fr'
    
    print("=" * 60)
    print("Fetching 100 Random Argo Floats from FTP")
    print("=" * 60)
    
    # Get 100 random float IDs
    float_ids = get_random_floats(ftp_server, count=100)
    
    if not float_ids:
        print("Failed to get float IDs")
        return
    
    success_count = 0
    
    for idx, float_id in enumerate(float_ids, 1):
        print(f"\n[{idx}/100] Processing float {float_id}")
        print("-" * 40)
        
        # Get DAC
        dac = get_dac_for_float(ftp_server, float_id)
        if not dac:
            continue
        
        # Download file
        file_path = download_latest_profile(ftp_server, float_id, dac)
        if not file_path:
            continue
        
        # Ingest into database
        print(f"  Ingesting into database...")
        success = await ingest_float_file(file_path, float_id)
        
        # Cleanup
        try:
            os.unlink(file_path)
        except:
            pass
        
        if success:
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"SUCCESS: Ingested {success_count}/100 floats")
    print("=" * 60)
    print("\nVerify by running:")
    print("  curl http://localhost:8000/api/v1/floats/")
    print("\nOr refresh your browser at http://localhost:8081")


if __name__ == "__main__":
    asyncio.run(main())
