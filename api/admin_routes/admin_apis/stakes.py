from aiohttp import http_exceptions
import fastapi
from fastapi import FastAPI, HTTPException, status, APIRouter

import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from api.admin_routes.util_stakes import get_stakes_from_db, set_stake_winner
from api.utils.dependancies import db_dependancy
from api.utils.util_stakes import get_user_stakes_where_user_is_owner_from_db, get_user_stakes_where_user_is_guest_from_db
from api.api_stakes import process_stakes_data


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
        # if none is found an empty list will be returned
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
        if db_stake_object is None:
            logger.error(f"stake {stake_id} not found")

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"stake {stake_id} not found"
            )

        return True

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while setting stake winner: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while settig stake owner: {str(e)}"
        )


@router.get('/all_user_stakes')
async def admin_get_all_user_stakes(db: AsyncSession, user_id: int):
    try:
        db_owner_stakes= await get_user_stakes_where_user_is_owner_from_db(db, user_id)
        db_guest_stakes= await get_user_stakes_where_user_is_guest_from_db(db, user_id)
        processed_stakes_data= await process_stakes_data(db_owner_stakes, db_guest_stakes)

        # we return the full stakes , sorting will be done in the frontend
        return processed_stakes_data

    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"an error occured while admin was getting all user stakes: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to get all user stakes from the backend by the admin, {str(e)}"
        )