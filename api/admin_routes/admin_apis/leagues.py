from math import e
from aiohttp import http_exceptions
import fastapi
from fastapi import APIRouter , status , HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic_schemas.league_schemas import LeagueBaseModel
from services.football_services.football_data_api import FootballDataService
from api.admin_routes.util_leagues import add_league_to_popular_leagues, get_league_by_id_from_db, get_leagues_list_from_db, get_popular_leagues_from_db, update_league_added_status_to_true_or_false
from api.utils.dependancies import db_dependancy
from services.football_services.football_data_api import football_data_api_service

import logging

logger= logging.getLogger(__name__)

router = APIRouter(
    prefix='/admin/leagues',
    tags=['leagues']
)

@router.get('/')
async def get_leagues_list(db : db_dependancy):
    """
    check if the leagues are in the database
    if not query the api for the leagues
    """
    db_leagues = await get_leagues_list_from_db(db)

    if not db_leagues:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
        detail="failed to fech the leagues data from the database")

    return db_leagues

@router.get('/popular_leagues')
async def get_popular_leagues_list(db : db_dependancy):
    try :
        db_popular_leagues = await get_popular_leagues_from_db(db)
        if not db_popular_leagues:
            logger.error(f'object returned from database is undefined : {db_popular_leagues}')
        return db_popular_leagues
    except Exception as e:
        logger.error(f'an error occured on the get_popular_leagues_endpoint {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
        detail=f'an error occured on the get_popular_leagues_endpoint {str(e)}', exc_info=True)
    ...

@router.post('/add_all_leagues_to_system')
async def add_leagues_to_system(db : db_dependancy):
    """
    this is a function for initialy adding the leagues to the database
    check if database is already popylate with leagues data
    """
    db_object = await get_leagues_list_from_db(db)
    if db_object:
        return {
            'message' : "the leagues are already present"
        }

    football_api_service = FootballDataService()
    
    try:
        await football_api_service.add_leagues(db)
    except Exception as e:
        print(f'an error occured , detail {e}')
        return {
            'status' : status.HTTP_500_INTERNAL_SERVER_ERROR ,
            'message' : "there was an error fetching football api data",
            'error_message' : f'{e}'
        }

@router.post('/add_league_fixtures_to_database_thus_making_it_a_popular_league')
async def add_league_fixtures_to_database(db : db_dependancy , league_id : int):
    """
    when a league's data / fixtures is added to the database 
    then it is automaticaly a popular league as it will be added to popular leagues by default
    the popular leagues is there to prevent us from suffering the problem of 
    searching through the super huger list of leagues in the normal leagues table
    """ 
    try :
        await football_data_api_service.add_fixutures_by_league_id(db ,league_id)

        # after the data has been sourced and added to the database we them make the league a popular leageu

        await add_league_to_popular_leagues(db, league_id)
        
        return {
            "message" : f"league of league id {league_id} has been added to the database succesfuly "
        }

    except HTTPException:
        await db.rollback()

        logger.error(f"an error occured while adding leageu fixtures to the database: {str(e)}",
        exc_info=True,
        extra={})

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured whle adding league fixtures to the database, {str(e)}"
        )



# utility function for the league endpoints

"""
handles both the process of: 
1) updating the fixture added column on the league object to 
2) adding the leageu to popular leagues table officialy
"""
async def make_league_a_popular_league(db : AsyncSession , league_id : int):
    try:
        # first we update the league added column to true on the league object
        # here we are updating it to true since we are adding matches to the system
        db_league_object= await update_league_added_status_to_true_or_false(db, league_id)
        if not db_league_object:
            logger.error(f"object returned from db is undefined, make_league_a_popular_league")

        # after doing that we need to add the leageu to popuare leagues table in the database
        db_league_object= LeagueBaseModel(db_league_object)
        db_popular_league_object= await add_league_to_popular_leagues(db,  db_league_object)

        if not db_popular_league_object:
            logger.error(f"populare leageu object returned from db in not as expected: make_leageu_a_popular_league")

    except HTTPException:
        raise
    
    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while making {league_id} a populare leageu, {str(e)}",
        exc_info=True,
        extra={
            "affected_league_id": league_id
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while making league of league id : {league_id} a populre leageu: {str(e)}"
        )