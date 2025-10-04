# FloatChat Backend

## Project Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py            # Database configuration and session management
│   ├── models.py              # SQLAlchemy ORM models
│   ├── schemas.py             # Pydantic schemas for API
│   ├── config.py              # Application configuration
│   ├── dependencies.py        # FastAPI dependencies
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── floats.py      # Float-related endpoints
│   │   │   │   ├── profiles.py    # Profile-related endpoints
│   │   │   │   ├── measurements.py # Measurement endpoints
│   │   │   │   ├── ai_query.py    # AI query endpoints
│   │   │   │   └── health.py      # Health check endpoints
│   │   │   └── api.py         # API router aggregation
│   │   └── deps.py            # API dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Core configuration
│   │   ├── security.py        # Security utilities
│   │   └── logging.py         # Logging configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py      # AI/LLM service integration
│   │   ├── data_ingestion.py  # Argo data ingestion service
│   │   ├── geospatial.py      # Geospatial query service
│   │   └── cache_service.py   # Caching service
│   └── utils/
│       ├── __init__.py
│       ├── argo_parser.py     # Argo data file parsing utilities
│       ├── geospatial_utils.py # Geospatial calculation utilities
│       └── data_validation.py  # Data validation utilities
├── scripts/
│   ├── __init__.py
│   ├── init_db.py             # Database initialization script
│   ├── ingest_data.py         # Data ingestion script
│   ├── migrate_db.py          # Database migration script
│   └── seed_data.py           # Sample data seeding script
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest configuration
│   ├── test_models.py         # Model tests
│   ├── test_schemas.py        # Schema tests
│   ├── test_api/
│   │   ├── __init__.py
│   │   ├── test_floats.py     # Float API tests
│   │   ├── test_profiles.py   # Profile API tests
│   │   └── test_ai_query.py   # AI query API tests
│   └── test_services/
│       ├── __init__.py
│       ├── test_ai_service.py
│       └── test_data_ingestion.py
├── alembic/                   # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── logs/                      # Application logs
├── data/                      # Local data storage (development)
├── .env                       # Environment variables (not in git)
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore file
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose for development
├── alembic.ini             # Alembic configuration
└── README.md               # This file
```

## Quick Start

1. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```bash
   python scripts/init_db.py
   ```

4. **Run Development Server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Models

### Float
- Represents Argo oceanographic floats
- Contains WMO ID, deployment coordinates, metadata
- Links to multiple profiles

### Profile
- Individual oceanographic profiles from floats
- Contains timestamp, location, and metadata
- Uses PostGIS for geospatial queries
- Links to multiple measurements

### Measurement
- Individual measurements within a profile
- Contains pressure, temperature, salinity, and other variables
- Includes quality control flags

## Environment Variables

See `.env.example` for all required environment variables.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
flake8 app/
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```
