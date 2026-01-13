from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import false
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_routes.util_admin import get_admin_by_admin_name
from api.utils.dependancies import bcrypt_context, admin_dependancy, db_dependancy

from datetime import datetime, timezone, timedelta
import Request
import jwt
import logging
import os
from dotenv import load_dotenv

from pydantic_schemas.users_schema import AdminToken

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/auth",
    tags=["admin/auth"],
    responses={404: {"description": "Not found"}},
)

ADMIN_AUTH_ALGORITHM= os.getenv('ADMIN_AUTH_ALGORITHM')
ADMIN_AUTH_SECRET_KEY= os.getenv('ADMIN_AUTH_SECRET_KEY')
ADMIN_REFRESH_ALGORITHM= os.getenv('ADMIN_REFRESH_ALGORITHM')
ADMIN_AUTH_SECRET_KEY= os.getenv('ADMIN_AUTH_SECRET_KEY')

async def create_admin_access_token( admin_name : str , admin_id : int , expires_delta : timedelta ):
    encode = {'sub' : admin_name , 'id' : admin_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp' : expires})
    return jwt.encode(encode , ADMIN_AUTH_SECRET_KEY , algorithm = ADMIN_AUTH_ALGORITHM) # and just like that we will have created the access token 

async def create_admin_refresh_token(admin_name : str , admin_id : int , expires_delta : timedelta):
    encode = {'sub' : admin_name , 'id' : admin_id }
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp' : expires})
    return jwt.encode(encode , ADMIN_AUTH_SECRET_KEY , algorithm = ADMIN_REFRESH_ALGORITHM)

async def authenticate_admin(admin_name: str, password: str , db: AsyncSession):
    try :
        admin= await get_admin_by_admin_name(admin_name, db)
        if not admin:
            return False

        if not bcrypt_context.verify(password, admin.hashed_password):
            return False
        
        return admin
    
    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"an error occured while trying to authenticate the admin",
        exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to authenticate the admin loggin in"
        )

# this is for the admin login
@router.post('/token' , response_model = AdminToken , status_code = status.HTTP_201_CREATED)
async def admin_login_for_access_token( 
    form_data : Annotated[OAuth2PasswordRequestForm , Depends()] , # this oauth2 thingy here is just a way for us to get login details by following th estandard for auth , its better than just sendin the raw json data : username : str and password : str 
    db : db_dependancy , request : Request):

    admin_name= form_data.username
    password= form_data.password

    admin = await authenticate_admin(admin_name, password , db )
    if not admin:
        raise HTTPException( status_code =status.HTTP_401_UNAUTHORIZED , detail = " could not authorize the user ")
    admin_access_token = await create_admin_access_token(admin.admin_name , admin.admin_id , timedelta(hours= 2))
    admin_refresh_token = await create_admin_refresh_token(admin.admin_name , admin.admin_id , timedelta(days= 4))
    return {
        'admin_access_token' : admin_access_token ,
        'admin_refresh_token' : admin_refresh_token , 
        'token_type' : 'bearer'
        }

# this is for the admin login token refreshing
@router.post('/token/refresh' ) # so this neans when querying this endpoint we structure it this way : /auth/token/refresh and this is based on the prefix at the start of the file 
async def get_new_access_token(data : refresh_user_dependancy):
    username = data.get('username')
    user_id = data.get('id')
    print("we are now extracting user data from the ")
    if username is None or user_id is None:
        raise HTTPException( status_code = status.HTTP_401_UNAUTHORIZED , detail = "error authenticating user")
    new_access_token = await create_access_token(username , user_id , timedelta(hours= 24))

    return {'access_token' : new_access_token , 'token_type' : 'bearer' }

# note : this endpoint created here we will use it in future requests when building the other secure endpoints 