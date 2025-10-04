"""
Update existing floats to include all measurements (not just 15).
This will re-download float data and add all measurements.
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
from sqlalchemy import select

async def update_float_measurements(float_id: int, wmo_id: str, dac: str):
    """Update a single float with all measurements."""
    ftp_server = 'ftp.ifremer.fr'
    base_path = f'/ifremer/argo/dac/{dac}/{wmo_id}/profiles/'
    
    try:
        print(f"\nProcessing float {wmo_id}...")
        ftp = ftplib.FTP(ftp_server, timeout=30)
        ftp.login()
        ftp.cwd(base_path)
        
        filenames = ftp.nlst()
        nc_files = sorted([f for f in filenames if f.endswith('.nc') and f.startswith(('R', 'D'))])
        
        if not nc_files:
            ftp.quit()
            return False
        
        # Get the latest file
        latest_file_name = nc_files[-1]
        
        tmp_file = tempfile.NamedTemporaryFile(suffix='.nc', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        with open(tmp_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {latest_file_name}', local_file.write)
        
        ftp.quit()
        
        # Open with xarray
        ds = xr.open_dataset(tmp_path)
        
        async with AsyncSessionLocal() as session:
            try:
                # Get existing profiles
                result = await session.execute(
                    select(Profile).where(Profile.float_id == float_id)
                )
                profiles = result.scalars().all()
                
                if not profiles:
                    print(f"  No profiles found for float {float_id}")
                    return False
                
                # Update each profile with ALL measurements
                for profile in profiles:
                    prof_idx = profile.cycle_number - 1
                    
                    if prof_idx >= ds.sizes.get('N_PROF', 0):
                        continue
                    
                    # Delete existing measurements
                    await session.execute(
                        select(Measurement).where(Measurement.profile_id == profile.id)
                    )
                    existing = (await session.execute(
                        select(Measurement).where(Measurement.profile_id == profile.id)
                    )).scalars().all()
                    
                    for m in existing:
                        await session.delete(m)
                    
                    # Add ALL measurements (not just 15)
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
                        
                        print(f"  Profile {profile.cycle_number}: Added {measurements_added} measurements")
                
                await session.commit()
                print(f"  ✓ Updated float {wmo_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"  Error: {e}")
                return False
        
    except Exception as e:
        print(f"  Error: {e}")
        return False
    finally:
        try:
            os.unlink(tmp_path)
            ds.close()
        except:
            pass

async def main():
    """Update all floats with full measurement data."""
    print("=" * 60)
    print("Updating Floats with Full Measurement Data")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # Get all floats
        result = await session.execute(select(Float))
        floats = result.scalars().all()
        
        print(f"\nFound {len(floats)} floats to update")
        
        # For each float, we need to know its DAC
        # We'll need to look it up from the FTP index
        success_count = 0
        
        for idx, float_obj in enumerate(floats[:10], 1):  # Update first 10 for testing
            print(f"\n[{idx}/10] Float {float_obj.wmo_id}")
            
            # Try to determine DAC from institution
            dac_map = {
                'AOML': 'aoml',
                'CORIOLIS': 'coriolis',
                'CSIO': 'csio',
                'CSIRO': 'csiro',
                'INCOIS': 'incois',
                'JMA': 'jma',
                'KORDI': 'kordi',
                'MEDS': 'meds',
                'NMDIS': 'nmdis'
            }
            
            dac = dac_map.get(float_obj.institution, 'aoml')  # Default to aoml
            
            success = await update_float_measurements(float_obj.id, float_obj.wmo_id, dac)
            if success:
                success_count += 1
    
    print("\n" + "=" * 60)
    print(f"SUCCESS: Updated {success_count}/10 floats with full measurements")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
