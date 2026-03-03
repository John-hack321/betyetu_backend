from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, case, outerjoin, or_

from pydantic import BaseModel

from db.models.model_users import User, Account
from db.models.model_stakes import Stake
from pydantic_schemas.stake_schemas import StakeStatus

import logging
import math

logger= logging.getLogger(__name__)

# for validation of the AllUsersReturnModel
class AllUsersReturnModel:
    id: int
    username: str
    phone: str
    account_balance: int
    email: str
    no_of_stakes: int
    no_of_pending_stakes: int

async def admin_get_all_users_from_db(db: AsyncSession, limit: int= 100, page: int= 1):
    try: 

        # we need the total count for the number of stakes the user has ( pedning and all in general )
        # we need the number of pedning stakes and other stakes too

        no_of_users= await db.scalar(select(func.count()).select_from(User))
        
        offset= (page - 1) * limit
        
        query= (select(
            User.id,
            User.username,
            User.phone,
            Account.balance.label("account_balance"),
            User.email,
            func.count(Stake.id).label('no_of_stakes'),
            func.count(
                case((Stake.stake_status == StakeStatus.pending, 1),
            )).label('no_of_pending_stakes')
        
        )
        .join(Account, Account.user_id == User.id)
        .outerjoin(
            Stake,
            or_(Stake.user_id == User.id, Stake.invited_user_id == User.id)
        ).group_by(User.id, Account.balance)
        .limit(limit)
        .offset(offset)
        )

        result= await db.execute(query)
        users_with_stakes_data: list[AllUsersReturnModel] = result.all()

        users_data= [
            {
                "id": row.id,
                "username": row.username,
                "phone_number": row.phone,
                "account_balance": row.account_balance,
                "email": row.email,
                "no_of_stakes": row.no_of_stakes,
                "no_of_pending_stakes": row.no_of_pending_stakes,
            }

            for row in users_with_stakes_data
        ]

        return {
            "page": page,
            "limit": limit,
            "total": no_of_users,
            "total_pages" : math.ceil(no_of_users / limit),
            "has_next_page": (page * limit) < no_of_users,
            "users_data": users_data
        }

    except Exception as e:
        logger.error(f"an error occured while trying to get all users from the db : {str(e)}", exc_info= True)

        raise HTTPException (
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail = f" an erro occured while admin was trying to get all users from the db"
        )