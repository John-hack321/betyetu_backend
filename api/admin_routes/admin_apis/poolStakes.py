from fastapi import APIRouter, HTTPException, status

from api.admin_routes.util_pool_stakes import db_populate_pool_stakes, db_get_all_pool_stakes

import logging
import sys

from api.utils.dependancies import db_dependancy

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

router = APIRouter(
    prefix='/admin/pool_stakes',
    tags=['admin/pool_stakes']
)

@router.post("/")
async def populate_db_with_pool_stake_from_current_stakes(db: db_dependancy, want_to_populate: bool): # add the admin dependancy for secutity too
    """
    this function is not that important , well it is now at the time of building but later on I dont think so 
    it populates the db with automatic system generated pool stakes that are in-house
    """
    try :
        # we will use True as the determiner for the endpoint to work
        if not want_to_populate:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="invalid request this endpoint only accepts true")

        db_populated_pool_stakes= await db_populate_pool_stakes(db)
        if db_populated_pool_stakes:
            return {
                "status_code" : 200, # we  use 200 for succes system-wide
                "message": "Pool stakes populated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to populate pool stakes")

    except Exception as e: 
        logger.error(f"an error occured while admin trying to populate the db with pool stakes: {e}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to populate pool stakes"
        )

@router.get("/admin_get_pool_stakes")
async def get_pool_stakes(db: db_dependancy, page: int= 1, limit: int= 100):
    """
    this function returns all the pool stakes in the database
    """
    try:
        # get all pool stakes from the database
        db_pool_stakes = await db_get_all_pool_stakes(db, page, limit)
        return db_pool_stakes

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"an error occured while admin trying to get pool stakes: {e}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pool stakes"
        )

