"""
Pytest configuration and fixtures for FloatChat backend tests.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from app.models import Float, Profile, Measurement
from app.config import settings


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

# Create test session maker
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database dependency override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_float(db_session: AsyncSession) -> Float:
    """Create a sample float for testing."""
    float_obj = Float(
        wmo_id="1901393",
        deployment_latitude=35.0,
        deployment_longitude=-140.0,
        platform_type="APEX",
        institution="WHOI",
        project_name="Argo_WHOI",
        pi_name="John Toole",
        status="active"
    )
    
    db_session.add(float_obj)
    await db_session.commit()
    await db_session.refresh(float_obj)
    
    return float_obj


@pytest_asyncio.fixture
async def sample_profile(db_session: AsyncSession, sample_float: Float) -> Profile:
    """Create a sample profile for testing."""
    from datetime import datetime
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point
    
    point = Point(-140.0, 35.0)
    location = from_shape(point, srid=4326)
    
    profile = Profile(
        float_id=sample_float.id,
        cycle_number=1,
        profile_id=f"{sample_float.wmo_id}_001",
        timestamp=datetime.utcnow(),
        latitude=35.0,
        longitude=-140.0,
        location=location,
        direction='A',
        data_mode='R'
    )
    
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    
    return profile


@pytest_asyncio.fixture
async def sample_measurements(db_session: AsyncSession, sample_profile: Profile) -> list:
    """Create sample measurements for testing."""
    measurements = []
    
    pressures = [10, 50, 100, 200, 500, 1000]
    
    for i, pressure in enumerate(pressures):
        measurement = Measurement(
            profile_id=sample_profile.id,
            pressure=pressure,
            depth=pressure * 0.98,
            temperature=20.0 - (pressure * 0.01),
            salinity=34.5 + (pressure * 0.001),
            measurement_order=i
        )
        
        measurements.append(measurement)
        db_session.add(measurement)
    
    await db_session.commit()
    
    for measurement in measurements:
        await db_session.refresh(measurement)
    
    return measurements


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    from unittest.mock import Mock
    from app.schemas import QueryParameters
    
    mock_service = Mock()
    
    # Mock process_query method
    mock_service.process_query.return_value = QueryParameters(
        location="Pacific Ocean",
        variables=["temperature", "salinity"],
        general_search_term="test query"
    )
    
    # Mock generate_insights method
    mock_service.generate_insights.return_value = "Test insights about oceanographic data."
    
    # Mock generate_recommendations method
    mock_service.generate_recommendations.return_value = [
        "Examine temperature profiles",
        "Compare with historical data",
        "Analyze seasonal patterns"
    ]
    
    return mock_service


@pytest.fixture
def sample_query_parameters():
    """Sample query parameters for testing."""
    from app.schemas import QueryParameters
    from datetime import datetime
    
    return QueryParameters(
        location="Pacific Ocean",
        bbox=[-180, -60, -70, 60],
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        variables=["temperature", "salinity"],
        depth_range=[0, 1000],
        general_search_term="Pacific temperature"
    )


@pytest.fixture
def sample_ai_query():
    """Sample AI query input for testing."""
    from app.schemas import AIQueryInput
    
    return AIQueryInput(
        question="Show me temperature data from the Pacific Ocean in 2023",
        context={"user_id": "test_user"}
    )


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
