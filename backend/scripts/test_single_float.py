"""
Test script to fetch and ingest a single Argo float from AWS S3.
"""
import asyncio
import sys
from pathlib import Path
import requests
import xarray as xr
from datetime import datetime
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Float, Profile, Measurement

async def test_single_float():
    """Fetch and ingest a single float from AWS S3."""
    
    # Argo GDAC AWS S3 public URL (no authentication needed)
    # Example: aoml/2902696 is a well-known float
    base_url = "https://argo-gdac-sandbox.s3.amazonaws.com"
    float_path = "aoml/2902696/2902696_prof.nc"
    file_url = f"{base_url}/{float_path}"
    
    print(f"Fetching float data from AWS S3...")
    print(f"URL: {file_url}")
    
    try:
        # Download the NetCDF file
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        print(f"Downloaded {len(response.content)} bytes")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        print(f"Saved to temporary file: {tmp_path}")
        
        # Open with xarray
        ds = xr.open_dataset(tmp_path)
        print(f"\nDataset variables: {list(ds.variables.keys())}")
        
        # Extract float metadata
        wmo_id = str(ds.attrs.get('platform_number', '2902696'))
        print(f"\nFloat WMO ID: {wmo_id}")
        print(f"Number of profiles: {ds.dims.get('N_PROF', 0)}")
        
        # Insert into database
        async with AsyncSessionLocal() as session:
            try:
                # Create float
                float_obj = Float(
                    wmo_id=wmo_id,
                    platform_type=str(ds.attrs.get('platform_type', 'APEX')),
                    institution=str(ds.attrs.get('institution', 'AOML')),
                    project_name=str(ds.attrs.get('project_name', 'Argo')),
                    status='active',
                    last_update=datetime.utcnow()
                )
                session.add(float_obj)
                await session.flush()
                print(f"\nCreated float in database: ID={float_obj.id}, WMO={float_obj.wmo_id}")
                
                # Process first profile only (for testing)
                if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
                    lat = float(ds['LATITUDE'].values[0])
                    lon = float(ds['LONGITUDE'].values[0])
                    
                    # Get timestamp
                    if 'JULD' in ds.variables:
                        juld = ds['JULD'].values[0]
                        # Convert to datetime (JULD is days since 1950-01-01)
                        from datetime import timedelta
                        timestamp = datetime(1950, 1, 1) + timedelta(days=float(juld))
                    else:
                        timestamp = datetime.utcnow()
                    
                    profile = Profile(
                        float_id=float_obj.id,
                        cycle_number=1,
                        profile_id=f"{wmo_id}_1",
                        timestamp=timestamp,
                        latitude=lat,
                        longitude=lon,
                        direction='A',
                        data_mode='R'
                    )
                    session.add(profile)
                    await session.flush()
                    print(f"Created profile: ID={profile.id}, Lat={lat:.2f}, Lon={lon:.2f}")
                    
                    # Add a few measurements
                    if 'PRES' in ds.variables and 'TEMP' in ds.variables:
                        pres = ds['PRES'].values[0]
                        temp = ds['TEMP'].values[0]
                        psal = ds['PSAL'].values[0] if 'PSAL' in ds.variables else None
                        
                        measurements_added = 0
                        for i in range(min(10, len(pres))):  # First 10 measurements
                            if not float('nan') == pres[i]:  # Skip NaN values
                                measurement = Measurement(
                                    profile_id=profile.id,
                                    pressure=float(pres[i]),
                                    depth=float(pres[i]) * 1.02,  # Approximate depth
                                    temperature=float(temp[i]) if not float('nan') == temp[i] else None,
                                    salinity=float(psal[i]) if psal is not None and not float('nan') == psal[i] else None,
                                    measurement_order=i
                                )
                                session.add(measurement)
                                measurements_added += 1
                        
                        print(f"Created {measurements_added} measurements")
                
                await session.commit()
                print(f"\n✓ Successfully ingested float {wmo_id} from AWS S3!")
                print(f"\nVerify by running:")
                print(f"  curl http://localhost:8000/api/v1/floats/")
                
            except Exception as e:
                await session.rollback()
                print(f"\nError inserting into database: {e}")
                raise
        
        # Cleanup
        import os
        os.unlink(tmp_path)
        
    except requests.exceptions.RequestException as e:
        print(f"\nError downloading file: {e}")
        raise
    except Exception as e:
        print(f"\nError processing file: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_single_float())
