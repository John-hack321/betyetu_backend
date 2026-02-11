from db.db_setup import Base
from db.models.mixins import TimeStamp

from sqlalchemy import String , Integer , ForeignKey , Text , DateTime , Boolean , Column, Enum
from sqlalchemy.orm import relationship

class TitleType(enum.Enum):
    coach= "coach"
    defenders= "defenders"
    keepers= "keepers"
    midfielders= "midfielders"
    attackers= "attackers"

class Player(Base, TimeStamp):
    __tablename__= "players"

    localId= Column(Integer, nullable=False, primary_key=True, unique=True, index= True)
    id= Column(Integer, nullalbe=True, unique= True)
    player_name= Column(String, nullable=False)
    title= Column(Enum(TitleType), nullable=True)
    height= Column(Integer, nullable=True)
    date_of_birth= Column(String, nullable=True)