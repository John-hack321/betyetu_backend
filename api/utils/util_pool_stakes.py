from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import joinedload

import math
import logging
import datetime
from pytz import timezone

from db.models.model_stakes import PoolStake
from db.models.model_fixtures import Fixture

NAIROBI_TZ = timezone('Africa/Nairobi')

logger = logging.getLogger(__name__)

async def db_user_get_all_pool_stakes(db: AsyncSession, page: int= 1, limit: int= 100): # no need to pass user here since it is not being used anywhere
    """
    this function returns all the pool stakes in the database
    filters out pool stakes that have passed the cutoff time (2 hours before current time)
    """
    try:
        # we first need to cound the number of stakes
        current_time_eat = datetime.datetime.now(NAIROBI_TZ).replace(tzinfo=None)
        match_cutoff_time = current_time_eat - datetime.timedelta(hours=2)
        
        count_query= select(func.count(PoolStake.id)).where(PoolStake.locks_at >= match_cutoff_time)
        total_stakes= await db.execute(count_query)
        total_stakes= total_stakes.scalar()

        offset = (page - 1) * limit
        query= select(PoolStake).options(joinedload(PoolStake.match)).where(PoolStake.locks_at >= match_cutoff_time).offset(offset).limit(limit)
        pool_stakes= await db.execute(query)
        pool_stakes= pool_stakes.scalars().all()
        
        # Format the response to include home_team and away_team
        formatted_pool_stakes = []
        for stake in pool_stakes:
            stake_data = {
                "id": stake.id,
                "match_id": stake.match_id,
                "league_id": stake.league_id,
                "stake_status": stake.stake_status,
                "locks_at": stake.locks_at,
                "resolution_date": stake.resolution_date,
                "outcome": stake.outcome,
                "pool_amount": stake.pool_amount,
                "home_pool": stake.home_pool,
                "away_pool": stake.away_pool,
                "draw_pool": stake.draw_pool,
                "home_pool_count": stake.home_pool_count,
                "away_pool_count": stake.away_pool_count,
                "draw_pool_count": stake.draw_pool_count,
                "created_at": stake.created_at,
                "updated_at": stake.updated_at,
                "home_team": stake.match.home_team if stake.match else None,
                "away_team": stake.match.away_team if stake.match else None
            }
            formatted_pool_stakes.append(stake_data)

        total_pages= math.ceil(total_stakes / limit)

        return {
            "page": page,
            "limit": limit,
            "total": total_stakes,
            "total_pages": total_pages,
            "has_next_page": page < total_pages,
            "has_previous_page": page > 1,
            "data": formatted_pool_stakes
        }

    except Exception as e:
        logger.error(f"an error occured while user trying to get all pool stakes {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while user getting all pool stakes : {e}"
        )

# we are now pushing to master before we start working on alembic