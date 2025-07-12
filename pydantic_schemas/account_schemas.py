import datetime
from pydantic import BaseModel
from pydantic_core.core_schema import timedelta_schema


class AccountBase(BaseModel):
    balance : int
    currency : str

class CreateAccountBalance(AccountBase):
    ...

class Account(AccountBase):
    created_at : datetime
    updataed_at : datetime
    
    class config:
        orm_model = True