from aiohttp import http_exceptions
import fastapi
from fastapi import FastAPI, HTTPException, status, APIRouter

import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from api.admin_routes.util_stakes import get_stakes_from_db, set_stake_winner
from api.utils.dependancies import db_dependancy


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

router = APIRouter(
    prefix='/admin/stakes',
    tags=['admin/stakes']
)

@router.get('/')
async def admin_get_user_stakes(db: db_dependancy):
    try:
        db_stakes= await get_stakes_from_db(db)
        if not db_stakes:
            logger.error(f"the stakes object returned from the db is not valid")
        return db_stakes

    except Exception as e:
        logger.error(f"an error occured whle getting user stakes as the admin: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured whle getting user stakes as the admin"
        )

# this is just for debugging and testing services okay
@router.post('/set_winner')
async def admin_set_winner(db: db_dependancy, stake_id: int, side: int): # 1 is for owner and 2 is for the 
    try:
        db_stake_object= await set_stake_winner(db, stake_id, side)
        if not db_stake_object:
            logger.error(f"the object returned for the db is ont defined")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"stake object returned from db is not defined"
            )

        return True

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while setting stake winner: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while settig stake owner: {str(e)}"
        )