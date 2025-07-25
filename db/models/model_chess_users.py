from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column , Text , String , Integer , Enum , ForeignKey 

from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.chess_player_schemas import country_code , account_status_code

class ChessProfile(Base , TimeStamp):
    __tablename__ = "chess_profile_table"

    id = Column(Integer , index=True , nullable=False , primary_key=True)
    user_id = Column(Integer ,ForeignKey('users.id') , nullable = False )
    player_id = Column(Integer, nullable=True , unique=True)
    username = Column(String(50) , nullable = True , unique = True)
    followers = Column(Integer , nullable = True , default=0)
    country = Column(Enum(country_code) , default = 254)
    account_status = Column(Enum(account_status_code) , default = 1 , ) # is for the basic status for the basic account on registration on chess.com 
    account_verification_status = Column(Boolean , default=False)
    league = Column(String(50) , default='wood') # wood i belive is for the most basic level for an account

    user = relationship("User" , back_populates='chess_profile')