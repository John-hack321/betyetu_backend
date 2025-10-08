from db.db_setup import Base
from pydantic_schemas.fixtures_schemas import MatchObject
from db.models.model_fixtures import Fixture

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import status

async def add_match_to_db(db : AsyncSession , match_data : MatchObject):

    db_object = Fixture(
        match_id= match_data.match_id,
        home_team_id= match_data.home_team_id,
        home_team= match_data.home_team,
        away_team_id= match_data.away_team_id,
        away_team= match_data.home_team,
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

