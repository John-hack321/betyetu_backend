from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from db.db_setup import Base
from db.models.mixins import TimeStamp

class Season(Base, TimeStamp):
    __tablename__ = "seasons"

    local_id= Column(Integer, nullable=False, index=True, primary_key=True)
    id= Column(Integer, nullable=True)
    season_year_string= Column(String, nullable=True)

    # Use string references
    teams= relationship("Team", back_populates="season")
    fixtures= relationship("Fixture", back_populates="season")