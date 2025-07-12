from collections import UserList
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text
from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.transaction_schemas import tr_type

# user based models go here 

class User( TimeStamp , Base): # this base here is the declarative instance object from the db_setup file 
    __tablename__ = "users"

    id = Column(Integer , index = True , primary_key = True )
    email = Column(String(50) , nullable = False , unique = True )
    phone = Column(String(50) , nullable = False , unique = True )
    username = Column(String(50) , nullable = False )
    hashed_password = Column(String)

    accounts = relationship("Account" , uselist = False ,back_populates = "users")
    transactions = relationship("Transactions" , back_populates = "users")

# account based models go here

class Account(TimeStamp , Base):
    __tablename__ = "accounts"

    id = Column(Integer , index = True , primary_key = True)
    balance = Column(Integer , nullable = False , default = 0)
    user_id = Column(Integer ,ForeignKey("users.id"), nullable = False )
    currency = Column(String(50) , nullable = False , default = "KES")

    users = relationship("User" , back_populates = "accounts")
    transactions = relationship("Transaction" ,  back_populates = "accounts")

# transaction based models go here 

class Transactions(TimeStamp , Base):
    __tablename__ = "transactions"

    id = Column(Integer , index = True , primary_key = True)
    user_id = Column(Integer , ForeignKey("users.id") , nullable = False)
    account_id = Column(Integer , ForeignKey("accounts.id") , nullable = False)
    ammount = Column(Integer)
    transaction_type = Column(Enum(tr_type))

    users = relationship("User" , back_populates = "transactions")
    accounts = relationship("Account" , back_populates = "transactions")