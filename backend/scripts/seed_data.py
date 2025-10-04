#!/usr/bin/env python3
"""
Sample data seeding script for FloatChat backend development.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal, init_db
from app.models import Float, Profile, Measurement
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_sample_floats():
    """Create sample float data for development and testing."""
    
    async with AsyncSessionLocal() as session:
        try:
            # Sample float data based on real Argo floats
            sample_floats = [
                {
                    "wmo_id": "1901393",
                    "deployment_latitude": 35.0,
                    "deployment_longitude": -140.0,
                    "platform_type": "APEX",
                    "institution": "WHOI",
                    "project_name": "Argo_WHOI",
                    "pi_name": "John Toole",
                    "status": "active"
                },
                {
                    "wmo_id": "1901394", 
                    "deployment_latitude": 25.5,
                    "deployment_longitude": -155.0,
                    "platform_type": "SOLO",
                    "institution": "SIO",
                    "project_name": "Argo_SIO",
                    "pi_name": "Dean Roemmich",
                    "status": "active"
                },
                {
                    "wmo_id": "1901395",
                    "deployment_latitude": 45.2,
                    "deployment_longitude": -125.8,
                    "platform_type": "APEX",
                    "institution": "UW",
                    "project_name": "Argo_UW",
                    "pi_name": "Susan Wijffels",
                    "status": "active"
                },
                {
                    "wmo_id": "1901396",
                    "deployment_latitude": -10.5,
                    "deployment_longitude": 165.0,
                    "platform_type": "PROVOR",
                    "institution": "CSIRO",
                    "project_name": "Argo_Australia",
                    "pi_name": "Susan Wijffels",
                    "status": "maintenance"
                },
                {
                    "wmo_id": "1901397",
                    "deployment_latitude": 55.0,
                    "deployment_longitude": -45.0,
                    "platform_type": "APEX",
                    "institution": "BIO",
                    "project_name": "Argo_Canada",
                    "pi_name": "Igor Yashayaev",
                    "status": "inactive"
                }
            ]
            
            created_floats = []
            
            for float_data in sample_floats:
                # Create float
                float_obj = Float(
                    wmo_id=float_data["wmo_id"],
                    deployment_latitude=float_data["deployment_latitude"],
                    deployment_longitude=float_data["deployment_longitude"],
                    platform_type=float_data["platform_type"],
                    institution=float_data["institution"],
                    project_name=float_data["project_name"],
                    pi_name=float_data["pi_name"],
                    status=float_data["status"],
                    deployment_date=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                    last_update=datetime.utcnow()
                )
                
                session.add(float_obj)
                await session.flush()  # Get the ID
                
                # Create profiles for this float
                await create_sample_profiles(session, float_obj)
                
                created_floats.append(float_obj)
                logger.info(f"Created float {float_obj.wmo_id} with profiles")
            
            await session.commit()
            logger.info(f"Successfully created {len(created_floats)} sample floats")
            
            return created_floats
            
        except Exception as e:
            logger.error(f"Error creating sample floats: {e}")
            await session.rollback()
            raise


async def create_sample_profiles(session, float_obj: Float):
    """Create sample profiles for a float."""
    
    # Generate 10-50 profiles per float
    num_profiles = random.randint(10, 50)
    
    base_lat = float_obj.deployment_latitude
    base_lon = float_obj.deployment_longitude
    
    for i in range(num_profiles):
        # Simulate float drift (small random movements)
        lat_drift = random.uniform(-2.0, 2.0)
        lon_drift = random.uniform(-3.0, 3.0)
        
        latitude = base_lat + lat_drift
        longitude = base_lon + lon_drift
        
        # Ensure coordinates are within valid ranges
        latitude = max(-90, min(90, latitude))
        longitude = max(-180, min(180, longitude))
        
        # Create profile timestamp (going back in time)
        days_ago = num_profiles - i
        timestamp = datetime.utcnow() - timedelta(days=days_ago * 10)  # Every 10 days
        
        # Create geometry point
        point = Point(longitude, latitude)
        location = from_shape(point, srid=4326)
        
        profile = Profile(
            float_id=float_obj.id,
            cycle_number=i + 1,
            profile_id=f"{float_obj.wmo_id}_{i+1:03d}",
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            location=location,
            direction='A',
            data_mode='R' if i < num_profiles - 5 else 'A'  # Last few profiles are adjusted
        )
        
        session.add(profile)
        await session.flush()  # Get profile ID
        
        # Create measurements for this profile
        await create_sample_measurements(session, profile)


async def create_sample_measurements(session, profile: Profile):
    """Create sample measurements for a profile."""
    
    # Generate measurements at standard depths
    standard_pressures = [
        5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500,
        600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1750, 2000
    ]
    
    # Add some random variation
    num_measurements = random.randint(15, len(standard_pressures))
    selected_pressures = sorted(random.sample(standard_pressures, num_measurements))
    
    for i, pressure in enumerate(selected_pressures):
        # Generate realistic oceanographic values
        
        # Temperature decreases with depth
        if pressure < 100:
            temperature = random.uniform(15.0, 25.0) - (pressure * 0.1)
        elif pressure < 1000:
            temperature = random.uniform(2.0, 8.0) - (pressure * 0.002)
        else:
            temperature = random.uniform(1.0, 4.0)
        
        # Salinity varies by region and depth
        base_salinity = 34.5
        if profile.latitude > 40:  # Higher latitudes
            base_salinity = 34.0
        elif abs(profile.latitude) < 20:  # Tropical regions
            base_salinity = 35.0
        
        salinity = base_salinity + random.uniform(-0.5, 0.5)
        
        # Dissolved oxygen decreases with depth
        if pressure < 200:
            dissolved_oxygen = random.uniform(200, 300)
        elif pressure < 1000:
            dissolved_oxygen = random.uniform(50, 150)
        else:
            dissolved_oxygen = random.uniform(150, 250)
        
        # pH varies slightly
        ph = random.uniform(7.8, 8.2) - (pressure * 0.0001)
        
        # Add some missing values to simulate real data
        if random.random() < 0.1:  # 10% chance of missing temperature
            temperature = None
        if random.random() < 0.15:  # 15% chance of missing salinity
            salinity = None
        if random.random() < 0.3:  # 30% chance of missing oxygen
            dissolved_oxygen = None
        if random.random() < 0.5:  # 50% chance of missing pH
            ph = None
        
        measurement = Measurement(
            profile_id=profile.id,
            pressure=pressure,
            depth=pressure * 0.98,  # Approximate depth conversion
            temperature=temperature,
            salinity=salinity,
            dissolved_oxygen=dissolved_oxygen,
            ph=ph,
            measurement_order=i
        )
        
        session.add(measurement)


async def main():
    """Main seeding function."""
    logger.info("Starting sample data seeding...")
    
    # Initialize database first
    await init_db()
    logger.info("Database initialized")
    
    # Create sample data
    floats = await create_sample_floats()
    
    logger.info(f"Sample data seeding completed! Created {len(floats)} floats with profiles and measurements.")
    
    # Print summary
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        
        # Count totals
        float_count = await session.execute(select(func.count(Float.id)))
        profile_count = await session.execute(select(func.count(Profile.id)))
        measurement_count = await session.execute(select(func.count(Measurement.id)))
        
        logger.info(f"Database now contains:")
        logger.info(f"  - {float_count.scalar()} floats")
        logger.info(f"  - {profile_count.scalar()} profiles") 
        logger.info(f"  - {measurement_count.scalar()} measurements")


if __name__ == "__main__":
    asyncio.run(main())
