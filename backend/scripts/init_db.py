#!/usr/bin/env python3
"""
Database initialization script for FloatChat backend.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db, engine
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_database_tables():
    """Create all database tables."""
    try:
        logger.info("Initializing database tables...")
        await init_db()
        logger.info("Database tables created successfully!")
        
        # Test database connection
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            logger.info("Database connection test successful")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def main():
    """Main initialization function."""
    logger.info(f"Initializing {settings.APP_NAME} database...")
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[0]}@***")
    
    await create_database_tables()
    
    logger.info("Database initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())
