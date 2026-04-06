from fastapi import APIRouter, HTTPException, status

import logging
import sys

from api.utils.dependancies import db_dependancy, user_dependancy
from api.utils.util_pool_stakes import db_user_get_all_pool_stakes
from pydantic_schemas.pool_stake_schemas import poolStakeJoiningPyalod
from api.utils.util_accounts import check_if_user_balance_is_enough
from api.utils.util_pool_stakes import confirm_if_stake_is_not_locked
from api.utils.util_pool_stakes import finaly_proecess_user_pool_stake_join

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

# self generated poolStakeStatusCodes :
# - 1000 : stake has been locked

router = APIRouter(
    prefix='/pool_stakes',
    tags=['/pool_stakes']
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

@router.post('/user_join_pool_stake')
async def user_join_pool_stake(db: db_dependancy, user: user_dependancy, pool_stake_data: poolStakeJoiningPyalod):
    """DNS_PROBE_STARTED
    this function allows a user to join a pool stake
    """
    try:
        await check_if_user_balance_is_enough(db, user.get('user_id'), pool_stake_data.userStakeAmount)
        await confirm_if_stake_is_not_locked(db, pool_stake_data.poolStakeId)

        #if those two main conditions pass we now add the user to the stake and perfrom all atomic operations
        await finaly_proecess_user_pool_stake_join(db, user.get('user_id'), pool_stake_data)

        return {"message": "Successfully joined pool stake"}

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"an error occured while user trying to join pool stake: {e}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join pool stake"
        )