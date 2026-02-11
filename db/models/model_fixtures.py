import datetime
from turtle import back
from db.db_setup import Base
from db.models.mixins import TimeStamp

from sqlalchemy import String , Integer , ForeignKey , Text , DateTime , Boolean , Column, Enum
from sqlalchemy.orm import relationship
import enum

class FixtureStatus(enum.Enum):
    live= "live"
    future= "future"
    expired= "expired"

class Fixture(Base , TimeStamp):
    __tablename__ = "fixtures"

    # reight now we hav alot of redundancies mostly when it comes to teams part but we will fix that later on
    local_id= Column(Integer, nullable=False, primary_key=True)
    match_id= Column(Integer, nullable=True)
    team_id= Column(Integer, ForeignKey("teams.local_id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.local_id"), nullable=False)
    home_team_id= Column(Integer, nullable=False)
    home_team= Column(String, nullable=False)
    away_team_id= Column(Integer, nullable=False)
    away_team= Column(String, nullable=False)
    match_date= Column(DateTime, nullable=False)
    is_played= Column(Boolean, nullable=False, default=False)
    outcome= Column(String, nullable=True) # stores the string outcome of the match in string format seperated by a hyphen
    home_score= Column(Integer, default=0)
    away_score= Column(Integer, default=0)
    fixture_status= Column(Enum(FixtureStatus), default= FixtureStatus.future)
    winner= Column(String, nullable=True) # stores the name of the winning team I think right

    league= relationship("League" , back_populates="fixtures")
    stakes = relationship('Stake', back_populates="match") # this is a many to one relationship with respect to the match object
    team= relationship("Team", back_populates="fixtures")