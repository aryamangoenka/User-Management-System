"""
Database table creation script
"""

import asyncio
from sqlalchemy import create_engine
from .database import metadata
from .config import settings


async def create_tables():
    """Create all database tables"""
    
    if settings.USE_SQLITE:
        # For SQLite, use synchronous engine
        sync_url = settings.SQLITE_URL.replace('+aiosqlite', '')
        engine = create_engine(sync_url, echo=True)
    else:
        # For PostgreSQL, use synchronous engine
        sync_url = settings.DATABASE_URL.replace('+asyncpg', '+psycopg2')
        engine = create_engine(sync_url, echo=True)
    
    print("Creating database tables...")
    metadata.create_all(engine)
    print("Database tables created successfully!")
    
    engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables()) 