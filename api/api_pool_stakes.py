from fastapi import APIRouter, HTTPException, status

import logging
import sys

from api.utils.dependancies import db_dependancy, user_dependancy
from api.utils.util_pool_stakes import db_user_get_all_pool_stakes

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

@router.get("/get_all_pool_stakes")
async def get_all_pool_stakes(db: db_dependancy, user: user_dependancy, page: int= 1, limit: int= 100):
    """
    this function returns all the pool stakes in the database
    """
    try:
        # get all pool stakes from the database
        db_pool_stakes = await db_user_get_all_pool_stakes(db, page, limit)
        return db_pool_stakes

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"an error occured while admin trying to get pool stakes: {e}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pool stakes"
        )
