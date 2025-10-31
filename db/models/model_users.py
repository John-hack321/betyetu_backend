from turtle import back
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text

from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.transaction_schemas import trans_type , trans_status

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
    owned_stakes = relationship("Stake", back_populates='user', foreign_keys='[Stake.user_id]')
    invited_stakes = relationship("Stake", back_populates='invited_user', foreign_keys='[Stake.invited_user_id]')

    # reminder : uselist is at flase for the account relationship because its is a one to one relationship yet for most relationships in sqlalchemy they are asumed to be one to many relationships

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
    amount = Column(Integer)
    transaction_type = Column(Enum(trans_type))
    status = Column(Enum(trans_status) , default = 2)
    merchant_request_id = Column(String(50) , nullable = True)
    merchant_checkout_id = Column(String(50) , nullable = True)
    receipt_number = Column(String(50) , nullable = True , default = None)
    ConversationID = Column(String(50) , nullable = True , default = None)
    OriginatorConversationID = Column(String(50) , nullable = True , default = None)


    user = relationship("User" , back_populates = "transactions")
    account = relationship("Account" , back_populates = "transactions")