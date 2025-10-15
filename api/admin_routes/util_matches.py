from sys import exc_info

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from db.db_setup import Base
from pydantic_schemas.fixtures_schemas import MatchObject
from db.models.model_fixtures import Fixture
from db.models.model_leagues import League

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status

import math
import logging

logger = logging.getLogger(__name__)

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

"""
the function will be sending the fixture data to the frontend in chunks of 100 per page 
"""
async def get_all_fixtures_from_db(db : AsyncSession , limit : int=100, page : int = 1):
    offset = (page - 1) * limit
    total= await db.scalar(select(func.count()).select_from(Fixture))
    query= (
        select(Fixture, League.name.label("league_name"), League.logo_url.label("league_logo_url"))
        .join(League, Fixture.league_id == League.id)
        .limit(limit)
        .offset(offset)
    )
    result= await db.execute(query)
    rows= result.all()    

    if not rows:
        logger.error('an unexpected error occured : no fixtures found in the get all fixtures from db')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
            detail= "no fixtures found in the get_all_fixtures_from_db utility functoin "
        )
    
    fixtures = await convert_fixtures_result_object_from_to_db_desired_return_object(rows)

    return {
        "page" : page,
        "limit" : limit,
        "total" : total,
        "total_pages" : math.ceil(total / limit),
        "has_next_page" : (page * limit) < total,
        "data" : fixtures
    }


"""
i dont think we will ever use this but for now lets just leave it there , we will decide to delete it or leave it in future
"""
async def get_fixtures_by_popular_league_from_db(db : AsyncSession , league_id : int):
    query= select(Fixture).where(Fixture.league_id == league_id)
    result = await db.execute(query)
    return result.scalars().all()


# SOME UTILITY FUNCTIONS TO HELP THE DB_UTILITY_FUNCTION 
async def convert_fixtures_result_object_from_to_db_desired_return_object(rows):
    """
    takes in the all fixtures rows from db 
    """
    fixtures_with_league_data = []
    for row in rows:
        # first conver the fixture row to a dict for easier prosessing
        # we need to return only the data we are in need of 
        fixture_dict= row[0].__dict__
        parsed_fixture_object = {}

        parsed_fixture_object['match_id']= fixture_dict.get('match_id')
        parsed_fixture_object['match_date']= fixture_dict.get('match_date')
        parsed_fixture_object['league_id']= fixture_dict.get('league_id')
        parsed_fixture_object['league_name']= row.league_name
        parsed_fixture_object['league_logo_url']= row.league_logo_url
        parsed_fixture_object['home_team_id']= fixture_dict.get('home_team_id')
        parsed_fixture_object['home_team']= fixture_dict.get('home_team')
        parsed_fixture_object['away_team_id']= fixture_dict.get('away_team_id')
        parsed_fixture_object['away_team']= fixture_dict.get('away_team')

        fixtures_with_league_data.append(parsed_fixture_object)
    return fixtures_with_league_data