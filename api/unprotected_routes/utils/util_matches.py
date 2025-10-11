from db.db_setup import Base
from db.models.model_fixtures import Fixture

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future.engine import select

async def unprotected_get_fixtures_list_from_db(db : AsyncSession):
    query= select(Fixture)
    result= await db.execute(query)
    return result.scalars().all()
