import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.utils.dependancies import bcrypt_context
from db.models.model_users import Admin
from pydantic_schemas.admin_schemas import CreateAdminRequest

logger= logging.getLogger(__name__)

async def db_create_one_time_admin(db: AsyncSession, admin_data: CreateAdminRequest):
    try : 

        # first check if admin is present so that we prevent creation of more admins
        query= select(Admin)
        result= await db.execute(query)
        db_admin_object= result.scalars().all()

        if db_admin_object:
            # if this si true , we rais an error so that the other code is not executed
            logger.error(f"an admin is already present thus cannot create a new one")
            raise HTTPException(
                status_code= status.HTTP_409_CONFLICT,
                detail= f" an admin is already present : can't create a new one"
            )

        admin_object= Admin(
            admin_name= admin_data.admin_username,
            hashed_password= bcrypt_context.hash(admin_data.admni_password)
        )

        db.add(admin_object)
        await db.commit()
        await db.refresh(admin_object)

        return admin_object

    except Exception as e:
        await db.rollback()

        logger.error(f" an error occured while trying to create on time admin, {str(e)}", exc_info= True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"a error occured while trying to create one time admin : {str(e)}"
        )

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
