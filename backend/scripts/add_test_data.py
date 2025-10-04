"""
Add test float data to the database.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import Float, Profile, Measurement

async def add_test_floats():
    """Add test float data."""
    async with AsyncSessionLocal() as session:
        try:
            # Create 10 test floats in different ocean regions
            ocean_regions = [
                {"name": "North Atlantic", "lat_range": (30, 60), "lon_range": (-50, -10)},
                {"name": "South Pacific", "lat_range": (-40, -10), "lon_range": (150, -120)},
                {"name": "Indian Ocean", "lat_range": (-30, 10), "lon_range": (60, 100)},
                {"name": "Southern Ocean", "lat_range": (-60, -40), "lon_range": (-180, 180)},
            ]
            
            floats_created = 0
            for i in range(10):
                region = random.choice(ocean_regions)
                lat = random.uniform(*region["lat_range"])
                lon = random.uniform(*region["lon_range"])
                
                # Create float
                float_obj = Float(
                    wmo_id=f"190{1000 + i}",
                    deployment_latitude=lat,
                    deployment_longitude=lon,
                    platform_type="APEX",
                    institution="Test Institution",
                    project_name="FloatChat Test",
                    status=random.choice(["active", "active", "active", "maintenance"]),
                    deployment_date=datetime.utcnow() - timedelta(days=random.randint(100, 500)),
                    last_update=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                session.add(float_obj)
                await session.flush()
                
                # Create 3-5 profiles for each float
                num_profiles = random.randint(3, 5)
                for j in range(num_profiles):
                    profile_lat = lat + random.uniform(-2, 2)
                    profile_lon = lon + random.uniform(-2, 2)
                    
                    profile = Profile(
                        float_id=float_obj.id,
                        cycle_number=j + 1,
                        profile_id=f"{float_obj.wmo_id}_{j+1}",
                        timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 100)),
                        latitude=profile_lat,
                        longitude=profile_lon,
                        direction="A",
                        data_mode="R"
                    )
                    session.add(profile)
                    await session.flush()
                    
                    # Create 10-15 measurements for each profile
                    num_measurements = random.randint(10, 15)
                    for k in range(num_measurements):
                        pressure = k * 100 + random.uniform(0, 50)
                        measurement = Measurement(
                            profile_id=profile.id,
                            pressure=pressure,
                            depth=pressure * 1.02,
                            temperature=random.uniform(2, 25),
                            salinity=random.uniform(33, 37),
                            measurement_order=k
                        )
                        session.add(measurement)
                
                floats_created += 1
                print(f"Created float {floats_created}/10: WMO {float_obj.wmo_id} at ({lat:.2f}, {lon:.2f})")
            
            await session.commit()
            print(f"\n✅ Successfully added {floats_created} test floats to the database!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error adding test data: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_test_floats())
