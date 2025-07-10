# we will try to make this project as asyncronous as possible
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession , create_async_engine , AsyncEngine

import os
from typing import AsyncGenerator

from dotenv import load_dotenv

load_dotenv()

SQL_ALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL')

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
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def create_database() -> None:
    """
    Creates all tables in the database
    Should be called on application startup
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_database() -> None:
    """
    Drops all tables in the database
    Use with caution!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
"""
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
        await db.commit()
"""