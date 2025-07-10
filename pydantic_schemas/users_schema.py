from pydantic import BaseModel
from datetime import datetime

# defining the user model in fastapi for effective user management
class UserBase(BaseModel): # this is the base model and its for the general user user defintion 
    username : str
    email : str

class UserCreateRequest(UserBase): # this is for use in creating users 
    passowrd : str

class UserResponse(UserBase): # this  is for response models to the frontend i guess 
    created_at : datetime
    updated_at : datetime

    class config():
        orm_mode = True # since this is a repsonse model we need to set orm = true since its created from the database rather from the dictionary

class Token(BaseModel):
    access_token : str
    token_type : str   