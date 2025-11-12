import enum
from pydantic import BaseModel

class trans_type(enum.IntEnum):
    withdrawal = 2
    deposit = 1

class trans_status(enum.IntEnum):
    successfull = 1
    pending = 2
    failed = 0 

class TransactionBase(BaseModel):
    amount : int
    transaction_type : trans_type

class TransactionGeneral(TransactionBase):
    status : trans_status
    merchant_request_id : str
    merchant_checkout_id : str

class CreateTransaction(TransactionBase):
    ...

class TransactionResponse(TransactionBase): # this is the general response one for requests back to the frontend 
    status : str

    class config:
        orm_model = True


""" id = Column(Integer , index = True , primary_key = True)
    user_id = Column(Integer , ForeignKey("users.id") , nullable = False)
    account_id = Column(Integer , ForeignKey("accounts.id") , nullable = False)
    amount = Column(Integer)
    transaction_type = Column(Enum(trans_type))
    status = Column(Enum(trans_status))
    merchant_request_id = Column(string(50) , nullable = false)
    merchant_checkout_id = column(String(50) , nullable = false)
"""