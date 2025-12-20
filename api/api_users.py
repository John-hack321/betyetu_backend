import fastapi
from fastapi import APIRouter, HTTPException , status 
from api.utils.dependancies import db_dependancy , user_dependancy
from api.utils.util_users import get_user_and_account_data
from pydantic_schemas.users_schema import UserProfileResponse

import logging

logger= logging.getLogger(__name__)

router = APIRouter(
    prefix = "/users",
    tags = ["users"]
)

@router.get("/me" , status_code=status.HTTP_200_OK , response_model=UserProfileResponse) # here we are goint to write an endpoint for getting user data
async def get_profile_data( db : db_dependancy ,  user : user_dependancy ) :
    """
       gets user id of the current user 
       it then retireves the users account and profile info from the database
    """
    try:
        current_user_data = await get_user_and_account_data(db , user_id = user['user_id'])
        print("current user found successfuly")
        if not current_user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "user not found")
        print("user and user_data found successfully")
        
        return {
            'username' : current_user_data.username,
            'phone' : current_user_data.phone,
            'account_balance' : current_user_data.account.balance,
        }
    except Exception as e:
        logger.error(f'an unexpected error occured: __get_profile_data: detail: {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an unexpected error occured: __get_profile_data, details: {str(e)} ")
