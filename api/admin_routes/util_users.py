from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from db.models.model_users import User

import logging

logger= logging.getLogger(__name__)

async def admin_get_all_users_from_db(db: AsyncSession):
    try: 
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