from aiohttp import http_exceptions
import fastapi
from fastapi import status, HTTPException, APIRouter

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from api.utils.dependancies import db_dependancy, user_depencancy
from api.admin_routes.util_matches import get_all_fixtures_from_db
from api.admin_routes.util_matches import get_fixtures_by_popular_league_from_db

logger= logging.getLogger(__name__)

router = APIRouter(
    prefix='/fixtures',
    tags="/fixtures"
)

@router.get('/')
async def get_all_fixtures(db : db_dependancy , user : user_depencancy):
    try:
        db_all_fixtures_object = await get_all_fixtures_from_db(db)
        if not db_all_fixtures_object:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
            detail=f"an error occred while qurying the database for all fixures list object returned : {db_all_fixtures_object}")
        return db_all_fixtures_object
    except Exception as e:
        logger.error(f'an unexpected error occured in the get_all_fixtures endpoint {str(e)} ', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
        detail=f"an unexpected error occured on the get_all_fixtures_endpoing")

@router.get('/popular_leagues_fixtures')
async def get_popular_leagues_fixtures(db : db_dependancy , user : user_depencancy):
    try:
        db_popular_leagues_fixtures_object = await get_popular_leagues_fixtures_from_db(db)
        if not db_popular_leagues_fixtures_object:
            raise HTTPException(f'an error occured while querying the database for the populare leagues object_returned : {db_popular_leagues_fixtures_object}')
        return db_popular_leagues_fixtures_object
    except Exception as e:
        logger.error(f"the get_popular_leagues_endpoint failed {str(e)}", exec_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
        detail=f"an unexpected error occured on the get_popular_leagues_endpoint {str(e)}", exc_info=True)

@router.get('/fixtures_by_leagues')
async def get_fixtures_by_popular_league(db : db_dependancy , user : user_depencancy , league_id ):
    try :
        db_fixture_by_popular_leagues_object = await get_fixture_by_popular_league_from_db(db)
        if not db_fixture_by_popular_leagues_object:
            raise HTTPException(f'an error occured on the get_fixture_by_popular_league , object returned : {db_fixture_by_popular_leagues_object}')
    except Exception as e:
        logger.error(f'an unexpected error occured on the get_fixtures_by_popular_leagues {str(e)}', exc_info=True)
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an unexpected error occured on the get_fixtures_by_popular_leagues endpoint {str(e)}")