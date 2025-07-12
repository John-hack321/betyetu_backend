from collections import UserList
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text
from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.transaction_schemas import trans_type

# user based models go here 

class User( TimeStamp , Base): # this base here is the declarative instance object from the db_setup file 
    __tablename__ = "users"

    id = Column(Integer , index = True , primary_key = True )
    email = Column(String(50), nullable=False, unique=True)
    phone = Column(String(50), nullable=False, unique=True, default="")
    username = Column(String(50), nullable=False)
    hashed_password = Column(String)

    account = relationship("Account" , uselist = False ,back_populates = "user")
    transactions = relationship("Transaction" , back_populates = "user")

# account based models go here

class Account(TimeStamp , Base):
    __tablename__ = "accounts"

    id = Column(Integer , index = True , primary_key = True)
    balance = Column(Integer , nullable = False , default = 0)
    user_id = Column(Integer ,ForeignKey("users.id"), nullable = False )
    currency = Column(String(50) , nullable = False , default = "KES")

    user = relationship("User" , back_populates = "account")
    transactions = relationship("Transaction" ,  back_populates = "account")

# transaction based models go here 

class Transaction(TimeStamp , Base):
    __tablename__ = "transactions"

    id = Column(Integer , index = True , primary_key = True)
    user_id = Column(Integer , ForeignKey("users.id") , nullable = False)
    account_id = Column(Integer , ForeignKey("accounts.id") , nullable = False)
    ammount = Column(Integer)
    transaction_type = Column(Enum(trans_type))

    user = relationship("User" , back_populates = "transactions")
    account = relationship("Account" , back_populates = "transactions")