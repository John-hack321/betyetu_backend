# things to do : 

# define metthos for creating new seasons 
# define methods for sourcing seasons too

from aiohttp import http_exceptions
import fastapi
from fastapi import APIRouter, HTTPException, status

from api.utils.dependancies import db_dependancy
from api.admin_routes.util_seasons import db_create_new_season_in_db, db_get_all_seasons_object_list

import logging

logger= logging.getLogger(__name__)

router= APIRouter(
    prefix='/admin/seasons',
    tags=['admin/seasons']
)

@router.post('/create_new_season')
async def admin_create_new_season(db: db_dependancy, season_string: str ): # later on we will make this route by using admin dependancy
    try:
        db_new_season_object= await db_create_new_season_in_db(db, season_string)
        if not db_new_season_object:
            logger.error(f" the object returned form the db is not a valid db object")

        return db_new_season_object # I thik here we will always need teh season Id for crating new matches for the seaosn and stuff.

    except HTTPException:
        raise 

    except Exception as e:
        logger.error(f"an error occurred while trying to crate a new season: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to create a new season "
        )

@router.get('/get_all_available_seasons')
async def admin_get_all_available_seasons(db: db_dependancy):
    try: 
        db_sesons_object= await db_get_all_seasons_object_list(db)
        if not db_sesons_object:
            logger.error(f"sesons object returned from the db is not as defined")

        return db_sesons_object

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f" an error occured while trying to get all available sesons from the database: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured while trying to get all available seaons : {str(e)}"
        )

@router.delete('/delete_all_seasons')
async def admin_delete_all_seasons(): # this is not the official function for deleting all season it is just a test function for the dev stage the actual function will be crated alter on that will cater for deleting everything including everything tied to the functin 
    try:
        # the logic will live here
        pass

    except Exception as e:
        logger.error(f"an error occured while trying to delete the seasons in the databaase : {str(e)}",  exc_info= True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured while trying to delete all seasons data from the database"
        )