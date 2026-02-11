from asyncio import mixins
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text 

from db.db_setup import Base
from db.models.mixins import TimeStamp


class Season(Base, TimeStamp):
    __tablename__ = "seasons"

    local_id= Column(Integer, nullable=False, index=True, primary_key=True)
    id= Column(Integer, nullable= True)
    season_year_string= Column(String, nullable=True)

    teams= relationship("Team", back_populates="season")