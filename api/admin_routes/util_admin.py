import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models.model_users import Admin

logger= logging.getLogger(__name__)

async def get_admin_by_admin_name(admin_name: str, db: AsyncSession):
    try :
        query= select(Admin).where(Admin.admin_name== admin_name)
        result= await db.execute(query)
        db_admin_object= result.scalars().first()

        return db_admin_object

    except Exception as e:
        logger.error(f"an error occured while getting admin by admin name, {str(e)}",
        exc_info= True)

    raise HTTPException(
        status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail= f"an error occured while trying to get admin by admin name : {str(e)}"
    )