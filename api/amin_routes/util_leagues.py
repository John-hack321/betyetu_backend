from db.models.model_leagues import League , PopularLeague
from pydantic_schemas.league_schemas import LeagueBaseModel
from api.utils.dependancies import user_depencancy , db_dependancy
from db.db_setup import Base

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select



async def add_league_to_db(db : AsyncSession, league_data : LeagueBaseModel):
    db_league = League(
        id = league_data.id,
        name = league_data.name,
        localized_name = league_data.localized_name,
        logo_url = league_data.logo_url,
        fixture_added = False
    )

    db.add(db_league)
    await db.commit()
    await db.refresh(db_league)
    return db_league

async def get_leages_from_db(db : AsyncSession):
    query = select(League)
    result = await db.execute(query)
    return result.scalars().all()


async def get_league_by_id_from_db(db : AsyncSession, league_id):
    query = select(League).where(League.id == league_id)
    result = await db.execute(query)
    return result.scalars().first()