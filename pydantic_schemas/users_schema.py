from pydantic import BaseModel
from datetime import datetime

# defining the user model in fastapi for effective user management
class UserBase(BaseModel): # this is the base model and its for the general user user defintion 
    username : str
    email : str
    phone : str

class UserCreateRequest(UserBase): # this is for use in creating users 
    # for this one we would need user entered data such as username , email , phone , password 
    password : str


class UserResponse(UserBase): # this is the general model for response models to the frontend i guess 
    created_at : datetime
    updated_at : datetime

    class config():
        orm_model = True # since this is a repsonse model we need to set orm = true since its created from the database rather from the dictionary

class Token(BaseModel):
    access_token : str
    token_type : str   