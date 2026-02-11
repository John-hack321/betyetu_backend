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

"""
Class representing a player in the database.

Attributes:
    localId: The player's id in the local database.
    id: The player's id in the external database.
    player_name: The player's name.
    title: The player's title. Can be one of the following: coach, defenders, keepers, midfielders, attackers.
    height: The player's height.
    date_of_birth: The player's date of birth.

"""
class Player(Base, TimeStamp):
    __tablename__= "players"

    localId= Column(Integer, nullable=False, primary_key=True, unique=True, index= True)
    id= Column(Integer, nullable=True, unique= True)
    player_name= Column(String, nullable=False)
    title= Column(Enum(TitleType), nullable=True)
    height= Column(Integer, nullable=True)
    date_of_birth= Column(String, nullable=True)