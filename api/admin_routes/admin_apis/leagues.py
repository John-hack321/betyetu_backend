from aiohttp import http_exceptions
import fastapi
from fastapi import APIRouter , status , HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.model_leagues import PopularLeague
from services.football_services.football_data_api import FootballDataService
from api.admin_routes.util_leagues import add_league_to_popular_leagues, get_league_by_id_from_db, get_leagues_list_from_db, get_popular_leagues_from_db
from api.utils.dependancies import db_dependancy

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
    db_object = await get_leagues_from_db(db)
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

@router.post('/admin/add_league_fixtures_to_database_thus_making_it_a_popular_league')
async def add_league_fixtures_to_database(db : db_dependancy , league_id : int):
    """
    when a league's data / fixtures is added to the database 
    then it is automaticaly a popular league as it will be added to popular leagues by default
    the popular leagues is there to prevent us from suffering the problem of 
    searching through the super huger list of leagues in the normal leagues table
    """
    # desired functionality 
    #  add matches data of the leauge to the datbase , 
    #  add the league to popular leagues too

    try :
        football_api_service = FootballDataService()
        try :
            await football_api_service.add_fixutures_by_league_id(db ,league_id)
            # if the league data has been added succesfuly we update a few other things as below : 
            db_popular_league_object = await make_league_a_popular_league(db ,league_id)
            if not db_popular_league_object:
                logger.error(f'faile to make league : {league_id} a popular league')
            updated_league_status_object = await make_league_a_popular_league(db , league_id)
            if not updated_league_status_object:
                logger.error(f"faile to update leagues status , object return is {updated_league_status_object}")
            return {
                "message" : f"league of league id {league_id} has been added to the database succesfuly "
            }
        except Exception as e:
            logger.error(f'an unexpected error occurred on the FootballDataService {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'an unexpected error occurred on the FootballDataService: {str(e)}'
            )
    except Exception as e:
        logger.error(f'an error occurred on the add_league_fixtures_to_database endpoint: {str(e)}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'the add_league_fixtures_to_database_endpoint failed: {str(e)}'
        )



# utility function for the league endpoints
async def make_league_a_popular_league(db : AsyncSession , league_id):
    db_league_object = await get_league_by_id_from_db(db, league_id)
    if not db_league_object:
        logger.error(f'object returned from db was not expeced : {db_league_object}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
        detail=f"an error occured on make_league_a_popular_league")
    db_league_object= PopularLeague(db_league_object)
    db_popular_league_object = await add_league_to_popular_leagues(db)
    return db_popular_league_object


