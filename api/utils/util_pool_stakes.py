from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import joinedload

import math
import logging
import datetime
from pytz import timezone

from db.models.model_stakes import PoolStake, PoolStakeChoice, PoolStakeEntry, PoolStakeStatus
from db.models.model_fixtures import Fixture
from pydantic_schemas.pool_stake_schemas import poolStakeJoiningPyalod
from api.utils.util_accounts import subtract_stake_amount_from_db

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
        query= select(PoolStake).options(joinedload(PoolStake.match)).where(
            PoolStake.locks_at >= match_cutoff_time
        ).offset(offset).limit(limit).order_by(PoolStake.locks_at.asc())

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

async def get_pool_stake_by_id(db: AsyncSession, pool_stake_id: int):
    query= select(PoolStake).where(PoolStake.id == pool_stake_id)
    result= await db.execute(query)
    return result.scalars().first()

async def confirm_if_stake_is_not_locked(db: AsyncSession, pool_stake_id: int):
    try:
        pool_stake_data = await get_pool_stake_by_id(db, pool_stake_id)
        
        if pool_stake_data.stake_status == PoolStakeStatus.locked:
            logger.warning(f"Pool stake {pool_stake_id} is locked and cannot be joined")
            
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Stake is locked and cannot be joined"
            )

    except HTTPException:
        # Re-raise HTTP exceptions (like our locked stake error)
        raise
        
    except Exception as e:
        logger.error(f"An error occurred while confirming if the stake is locked: {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking stake status"
        )



# CORE LOGIC OPERATIONS => these are highly intricate operations that should not break at any cost

# processing user stake joining request
async def finaly_proecess_user_pool_stake_join(
    db: AsyncSession,
    user_id: int,
    user_pool_joining_payload: poolStakeJoiningPyalod):
    try:
        # all of these must all run without failure, if one failes then the whole process is reversed so that we dont have partial data writes
        await update_pool_stake_with_new_entry_data(db, user_pool_joining_payload)
        await subtract_stake_amount_from_db(db, user_id, user_pool_joining_payload.userStakeAmount)
        await create_new_stake_entry(db, user_id, user_pool_joining_payload)

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()

        logger.error(f"an occured while finally processing user stake joining request")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured while finally processing user stake joining: {str(e)}"
        )

async def update_pool_stake_with_new_entry_data(db: AsyncSession, user_pool_joining_payload: poolStakeJoiningPyalod):
    """
    updtes the specific pool stake model with the relevant data
    """
    try:
        query= select(PoolStake).where(PoolStake.id == user_pool_joining_payload.poolStakeId)
        result = await db.execute(query)
        db_pool_stake= result.scalars().first()

        # update the amounts for the differet pools based on palcement
        # in the process we also update the bet general pool amount and the pool count for the differnt pools too
        if user_pool_joining_payload.userStakeChoice == "home":
            # update home pool
            db_pool_stake.home_pool = db_pool_stake.home_pool + user_pool_joining_payload.userStakeAmount
            db_pool_stake.pool_amount = db_pool_stake.pool_amount + user_pool_joining_payload.userStakeAmount
            db_pool_stake.home_pool_count+=1 # update the count of the sides

        elif user_pool_joining_payload.userStakeChoice == "away":
            # update the away pool
            db_pool_stake.away_pool = db_pool_stake.away_pool + user_pool_joining_payload.userStakeAmount
            db_pool_stake.pool_amount = db_pool_stake.pool_amount + user_pool_joining_payload.userStakeAmount
            db_pool_stake.away_pool_count += 1

        elif user_pool_joining_payload.userStakeChoice == "draw":
            # update the draw pool
            db_pool_stake.draw_pool = db_pool_stake.draw_pool + user_pool_joining_payload.userStakeAmount
            db_pool_stake.pool_amount = db_pool_stake.pool_amount + user_pool_joining_payload.userStakeAmount
            db_pool_stake.draw_pool_count+=1

        else :
            # we will raise an error here since option is not in the system
            pass # for now we will just pass I will write the logic later on

        await db.commit()
        await db.refresh(db_pool_stake)
        return db_pool_stake

    except Exception as e:
        await db.rollback() # in case of failure we revers all operations

        logger.error(f" an error occured whle trying to update pool stake with new entry data: {str(e)}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to update pool stake with new entry data: {str(e)}"
        )

async def create_new_stake_entry(db: AsyncSession, user_id: int, pool_stake_joining_payload: poolStakeJoiningPyalod):
    try: 
        # an in-function utility function
        def work_out_placement(user_placement: str):
            if user_placement == "home":
                return PoolStakeChoice.home
            elif user_placement == "away":
                return PoolStakeChoice.away
            elif user_placement == "draw":
                return PoolStakeChoice.draw
            else:
                raise HTTPException(
                    status_code= status.HTTP_400_BAD_REQUEST,
                    detail= "Invalid stake choice"
                )

        stake_entry_data= PoolStakeEntry(
            pool_stake_id= pool_stake_joining_payload.poolStakeId,
            user_id= user_id,
            placement= work_out_placement(pool_stake_joining_payload.userStakeChoice),
            amount= pool_stake_joining_payload.userStakeAmount,
        )
        
        db.add(stake_entry_data)
        await db.commit()
        await db.refresh(stake_entry_data)
        return stake_entry_data

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while creating new stake entry: {str(e)}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while creating new stake entry: {str(e)}"
        )


# UTILITY FUNCTIONS