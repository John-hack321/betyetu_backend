from aiohttp import http_exceptions
import fastapi
from fastapi import APIRouter, status, HTTPException

import logging

from api.utils.dependancies import db_dependancy, user_depencancy
from api.admin_routes.util_leagues import get_leagues_list_from_db, get_popular_leagues_from_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix= "/leagues",
    tags=['leagues']
)

@router.get('/') # endpoint for getting all leagues list
async def user_get_leagues_list(db : db_dependancy , user : user_depencancy):
    try :
        db_user_leagues_list = await get_leagues_list_from_db()
        if not db_user_leagues_list:
            raise HTTPException(f"An error occured while trying to fetch leagues list from db : object returned : {db_user_leagues_list}")
        return db_user_leagues_list
    except Exception as e :
        logger.error(f'an unexpected error occured in user_get_leagues_list endpoint {str(e)} ', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"An error occured in user_get_leagues_list endpoint {str(e)}")

@router.get('/available') #by avaailabe we are only  by default referencing the popular leagues 
async def user_get_popular_leagues(db : db_dependancy , user : user_depencancy):
    try :
        db_popular_leagues = await get_popular_leagues_from_db(db)
        if not db_popular_leagues:
            raise HTTPException(f'An error occured while querying the database for the popular leagues : object_returned : {db_popular_leagues}')
        return db_popular_leagues
    except Exception as e :
        logger.error(f'An unexpected error occured in user_get_popular_leagues endpoint {str(e)}', exc_into=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
        detail=f"an unexpected errror occured on the user_get_popular_leagues {str(e)}")