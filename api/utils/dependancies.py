from fastapi import Depends , HTTPException , status 
from fastapi.security import OAuth2PasswordBearer 
from sqlalchemy.orm import Session

from typing import Annotated
from passlib.context import CryptContext
from jose import jwt , JWTError
from dotenv import load_dotenv
import os

from db.db_setup import get_db

load_dotenv()
SECRET_KEY = os.getenv('AUTH_SECRET_KEY')
ALGORITHM = os.getenv("ALGORITHM")  
REFRESH_ALGORITHM = os.getenv("REFRESH_ALGORITHM")
##   db_dependancy = Annotated[Session, Depends(get_db)] #This creates a reusable shortcut for injecting a database session (Session) from your custom get_db() function.

# here I am going to implement a few things whose function I still dont know but lets just go with it 
# these i think Im made to believe that they are important lines when it comes to the auth things in fastapi 

db_dependancy = Annotated[ Session , Depends(get_db)] # this is just similar to doing : db : Session = Depends(get_db) what this does is that it gives a shortcut for injecting a database sessoin : i guess into our utility functions 
bcrypt_context = CryptContext( schemes = ['bcrypt'] , deprecated = 'auto') # this is like our password fortress it allows us to hash and verify plain text agains hashed passwords 
oauth2_bearer = OAuth2PasswordBearer( tokenUrl = "/auth/token") # tells fastapi where to extrect the token 
oauth2_bearer_dependancy = Annotated[str , Depends(oauth2_bearer)]
# i think that im now gettng the hang of this so here is an example flow for this : 
# for example for the auth_bearer dependancy , so this is what it does so for the auth 2 bearer function what it does is it goes to the url and extracts the token 
# but now for the auth2_bearer_dependacy when used in a function what it says is first run this function ( the one enclosed in the Depends thing ) , then use the result 


# we are now going to implement the famous get_current_usr utility function 

async def get_current_user( token : oauth2_bearer_dependancy):
    try :
        payload = jwt.decode(token , SECRET_KEY , algorithms = ALGORITHM)
        username = payload.get('sub')
        user_id = payload.get('id')
        if username is None or user_id is None:
            print("missing username or userid")
            raise HTTPException( status_code = status.HTTP_401_UNAUTHORIZED , detail = " could not validate user")
        return { 'username' : username , 'user_id' : user_id}
    except :
        raise HTTPException( status_code = status.HTTP_401_UNAUTHORIZED  , detail = "could not validate user")

user_depencancy = Annotated[dict , Depends(get_current_user)] # and now our auth user validation dependacy is complete

# well this new dependancy function is going to look somewhat similar to the get_current_user function but we will use it for 
# decoding the access token and extractin the refresh token from it 

refresh_bearer = OAuth2PasswordBearer(tokenUrl = "/auth/refresh")
refresh_bearer_dependancy = Annotated[str , Depends(refresh_bearer)]

async def get_current_refresh_request_owner(token : refresh_bearer_dependancy):
    try:
        payload = jwt.decode(token , SECRET_KEY , algorithms=REFRESH_ALGORITHM)
        username = payload.get('sub')
        user_id = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException( status_code = status.HTTP_401_UNAUTHORIZED , detail = "could not validate the user")
        return {'username'  : username , 'id' : user_id }
    except:
        raise HTTPException( status_code = status.HTTP_401_UNAUTHORIZED , detail = "could not validate the user")

refresh_user_dependancy = Annotated[dict , Depends(get_current_refresh_request_owner)]