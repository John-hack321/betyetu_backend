from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from db.db_setup import Base
from db.models.mixins import TimeStamp

class Team(Base, TimeStamp):
    __tablename__ = "teams"

    local_id= Column(Integer, nullable=False, primary_key=True, index=True)
    id= Column(Integer, nullable=True)
    season_id= Column(Integer, ForeignKey("seasons.local_id"), nullable=True)
    league_id= Column(Integer, ForeignKey("leagues.local_id"), nullable=False)
    team_name= Column(String, nullable=False, unique=True)
    team_logo_url= Column(String, nullable=True)
    played= Column(Integer, nullable=True)

    # Use string references
    league= relationship("League", back_populates="teams")
    season= relationship("Season", back_populates="teams")