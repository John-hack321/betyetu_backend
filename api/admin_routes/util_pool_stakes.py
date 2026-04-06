from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import datetime

from db.models.model_fixtures import Fixture
from db.models.model_stakes import PoolStake
from db.db_setup import Base

import logging
import sys
import math

from pytz import timezone

NAIROBI_TZ = timezone('Africa/Nairobi')

logger= logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

async def db_populate_pool_stakes(db: AsyncSession):
    """
    this is the main functio that does all the fucking
    it populates the db with the pool stakes.
    get all matches from the db
    iterate though the matches creating a poolstake for each
    """
    try:
        query= select(Fixture).where(Fixture.is_played == False)
        match_data= await db.execute(query)
        db_match_data= match_data.scalars().all()

        # we now build the loop that handles these matches here
        for match_item in db_match_data:
            # for each item we need to create a match object and add it to the db
            # nots : NOTE => 
            # the resolution date we put into the the poolstake will be the match start time plus 2 hours : obviousely it will not takes us long to resolve the match , plus this is just a show to the usr , it has no actual effect on the system

            pool_stake_object= PoolStake(
                match_id=match_item.local_id,
                league_id=match_item.league_id,
                locks_at=match_item.match_date,
                resolution_date=match_item.match_date + datetime.timedelta(hours=2),
            )

            db.add(pool_stake_object)
            await db.commit()
            await db.refresh(pool_stake_object)

        return True

    except Exception as e:
        logger.error(f"an error occured while trying to populate the db with pool stakes {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while populating the database with data : {e}"
        )


async def db_get_all_pool_stakes(db: AsyncSession, page: int= 1, limit: int= 100):
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
        query= select(PoolStake).where(
            PoolStake.locks_at >= match_cutoff_time
        ).offset(offset).limit(limit).order_by(PoolStake.locks_at.asc())
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
        logger.error(f"an error occured while trying to get all pool stakes {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while getting all pool stakes : {e}"
        )
