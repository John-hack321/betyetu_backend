from sqlalchemy import Enum 
import enum
from pydantic import BaseModel

class tr_type(enum.IntEnum):
    withdrawal : 1
    deposit : 2

class TransactionBase(BaseModel):
    amount : int
    transaction_type : int

class CreateTransaction(TransactionBase):
    ...

class TransactionResponse(TransactionBase): # this is the general response one for requests back to the frontend 
    status : str

    class config:
        orm_model = True