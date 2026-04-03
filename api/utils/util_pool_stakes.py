from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy import func

import math
import logging

from db.models.model_stakes import PoolStake




logger = logging.getLogger(__name__)


async def db_user_get_all_pool_stakes(db: AsyncSession, page: int= 1, limit: int= 100): # no need to pass user here since it is not being used anywhere
    """
    this function returns all the pool stakes in the database
    """
    try:
        # we first need to cound the number of stakes
        count_query= select(func.count(PoolStake.id))
        total_stakes= await db.execute(count_query)
        total_stakes= total_stakes.scalar()

        query= select(PoolStake)
        pool_stakes= await db.execute(query)
        pool_stakes= pool_stakes.scalars().all()

        total_pages= math.ceil(total_stakes / limit)

        return {
            "page": page,
            "limit": limit,
            "total": total_stakes,
            "total_pages": total_pages,
            "pool_stakes": pool_stakes,
            "has_next_page": page < total_pages,
            "has_previous_page": page > 1,
            "data": pool_stakes
        }


    except Exception as e:
        logger.error(f"an error occured while user trying to get all pool stakes {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while user getting all pool stakes : {e}"
        )

# we are now pushing to master before we start working on alembic