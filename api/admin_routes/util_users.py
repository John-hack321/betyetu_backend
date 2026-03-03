from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from db.models.model_users import User
from db.models.model_stakes import Stake
from pydantic_schemas.stake_schemas import StakeStatus

import logging

logger= logging.getLogger(__name__)

async def admin_get_all_users_from_db(db: AsyncSession):
    try: 


        # we need the total count for the number of stakes the user has ( pedning and all in general )
        # we need the number of pedning stakes and other stakes too
        total_stake_count_query= select(func.count()).select(Stake).where()
        total_stakes_count_result= await db.execute(total_stake_count_query)


        total_pending_stakes_count_query= select(func.count()).select(Stake).where(
            Stake.stake_status == StakeStatus.pending
        )
        total_pending_stakes_count_result= await db.execute(total_pending_stakes_count_query)


        query= select(User)
        result= await db.execute(query)
        db_user_list_object= result.scalars().all()

        return db_user_list_object

    except Exception as e:
        logger.error(f"an error occured while trying to get all users from the db : {str(e)}", exc_info= True)

        raise HTTPException (
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail = f" an erro occured while admin was trying to get all users from the db"
        )