from datetime import timedelta , datetime , timezone
from typing import Annotated
import os

from fastapi import Depends , HTTPException , status , APIRouter
from pydantic import BaseModel 
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from starlette.status import HTTP_400_BAD_REQUEST
from api.utils.dependancies import bcrypt_context

from dotenv import load_dotenv
from api.utils.dependancies import ALGORITHM, SECRET_KEY, bcrypt_context , db_dependancy 
from db.models.model_users import User
from pydantic_schemas.users_schema import Token , UserCreateRequest
from api.utils.util_users import create_user , get_user_by_username , get_user_by_email

load_dotenv()

router = APIRouter(
    prefix = '/auth',
    tags = ['auth']
)

SECRET_KEY = os.getenv('AUTH_SECRET_KEY')
ALGORITHM = os.getenv('AUTH_ALGORITHM')

# now we are going to create some functinality for the authentication itself 
# user auth function 

async def authenticate_user(username : str , password : str , db ):
    user = await get_user_by_username( username , db)
    if not user:
        return False
    if not bcrypt_context.verify(password , user.hashed_password):
        return False
    return user

# now lets build another function for generating the authentication token 

def create_access_token( username : str , user_id : int , expires_delta : timedelta ):
    encode = {'sub' : username , 'id' : user_id}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp' : expires})
    return jwt.encode(encode , SECRET_KEY , algorithm = ALGORITHM) # and just like that we will have created the access token 

# ENDPOINTS

@router.post('/' , status_code = status.HTTP_201_CREATED)
async def add_user( db : db_dependancy , user : UserCreateRequest):
    db_user = await get_user_by_email(db , user.email)
    if db_user:
        raise HTTPException( status_code = status.HTTP_409_CONFLICT , detail = "email is already registered")
    new_db_user = await create_user( db  , user)
    # okay im being told here that after create ing the new user we are supposed to return the access token so that the user gets logged in immediately 
    token = create_access_token(new_db_user.username , new_db_user.id , timedelta(minutes = 20))
    return {'access_token' : token , 'token_type' : 'bearer' }
    # return new_db_user we therefor obstruc this since we are not returning it to the backend 

# lets create another endpoint for getting the access token and sedning it back to the user

@router.post('/token' , response_model = Token , status_code = status.HTTP_201_CREATED)
async def login_for_access_token( 
    form_data : Annotated[OAuth2PasswordRequestForm , Depends()] , # this oauth2 thingy here is just a way for us to get login details by following th estandard for auth , its better than just sendin the raw json data : username : str and password : str 
    db : db_dependancy ):
    user = await authenticate_user(form_data.username , form_data.password , db )
    if not user:
        raise HTTPException( status_code =status.HTTP_401_UNAUTHORIZED , detail = " could not authorize the user ")
    token = create_access_token(user.username , user.id , timedelta(minutes = 20))
    return {'access_token' : token , 'token_type' : 'bearer' }