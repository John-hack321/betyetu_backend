import fastapi
from fastapi import APIRouter, HTTPException, status

from api.admin_routes.util_users import admin_get_all_users_from_db
from api.utils.dependancies import admin_dependancy

import logging

from api.utils.dependancies import db_dependancy

logger= logging.getLogger(__name__)

router= APIRouter(
    prefix="/admin/users",
    tags=['admin/users']
)

@router.get('/get_all_users')
async def admin_get_all_users(db: db_dependancy, admin: admin_dependancy): # we need to make this paginated if it is not yet paginated
    try:
        db_users_object= await admin_get_all_users_from_db(db)
        if not db_users_object:
            # I thnk this is a senirio when ther are no users in the system
            raise HTTPException(
                status_code= status.HTTP_204_NO_CONTENT,
                detail = f"there are no users registered in the system yet"
            )

        return db_users_object

    except HTTPException:
        raise 

    except Exception as e:
        logger.error(f"there was an error as admin was trying to query all users from the database: {str(e)}", exc_info= True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to get all users from the database, {str(e)}"
        )