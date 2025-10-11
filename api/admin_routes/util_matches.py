from db.db_setup import Base
from pydantic_schemas.fixtures_schemas import MatchObject
from db.models.model_fixtures import Fixture

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import status

# this is solely for the admin
async def add_match_to_db(db : AsyncSession , match_data : MatchObject):

    db_object = Fixture(
        match_id= match_data.match_id,
        league_id=match_data.league_id,
        home_team_id= match_data.home_team_id,
        home_team= match_data.home_team,
        away_team_id= match_data.away_team_id,
        away_team= match_data.away_team,
        match_date= match_data.match_date,
        is_played= match_data.is_played,
        outcome= match_data.outcome,
        home_score= match_data.home_score,
        away_score= match_data.away_score,
    )

    db.add(db_object)
    await db.commit()
    await db.refresh(db_object)
    return db_object

async def get_all_fixtures_from_db(db : AsyncSession):
    query= select(Fixture)
    result= await db.execute(query)
    return result.scalars().all()

async def get_fixtures_by_popular_league_from_db(db : AsyncSession , league_id : int):
    query= select(Fixture).where(Fixture.league_id == league_id)
    result = await db.execute(query)
    return result.scalars().all()