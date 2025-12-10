# we will try to make this project as asyncronous as possible
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession , create_async_engine , AsyncEngine

import os
from typing import AsyncGenerator

from dotenv import load_dotenv

load_dotenv('.env') # common testing a general variables
load_dotenv('.env.prod' , override=True) # similer prod variables will overide the local ones

# changin the database url to the production database now
SQL_ALCHEMY_DATABASE_URL = os.getenv('PROD_DATABASE_URL')

# These lines are not that important they are general fastapi setup code 
engine = create_async_engine( SQL_ALCHEMY_DATABASE_URL )
AsyncSessionLocal = sessionmaker( engine , class_= AsyncSession , expire_on_commit = False)
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields db sessions
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            # await session.close()
            pass

async def create_database() -> None:
    """
    Creates all tables in the database
    Should be called on application startup
    """
    async with engine.begin() as conn:
        # Drop all tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Then create all tables
        await conn.run_sync(Base.metadata.create_all)

from sqlalchemy import text

async def drop_database() -> None:
    """
    Drops all tables in the database
    Use with caution!
    """
    async with engine.begin() as conn:
        # Use SQLAlchemy's text() for raw SQL
        await conn.execute(text("SET session_replication_role TO 'replica'"))
        
        # Get all table names in the correct drop order
        result = await conn.execute(text(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            """
        ))
        tables = [row[0] for row in result]
        
        # Drop all tables with CASCADE
        for table in tables:
            await conn.execute(text(f'DROP TABLE IF EXISTS \"{table}\" CASCADE'))
        
        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role TO 'origin'"))
        await conn.commit()
"""
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
        await db.commit()
"""