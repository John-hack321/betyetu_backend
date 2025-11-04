import datetime
from db.db_setup import Base
from db.models.mixins import TimeStamp

from sqlalchemy import String , Integer , ForeignKey , Text , DateTime , Boolean , Column, Enum
from sqlalchemy.orm import relationship

class FixtureStatus(enum.Enum):
    live= 1
    future= 2
    expired= 3

class Fixture(Base , TimeStamp):
    __tablename__ = "fixtures"

    match_id= Column(Integer, nullable=False, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    home_team_id= Column(Integer, nullable=False)
    home_team= Column(String, nullable=False)
    away_team_id= Column(Integer, nullable=False)
    away_team= Column(String, nullable=False)
    match_date= Column(DateTime, nullable=False)
    is_played= Column(Boolean, nullable=False, default=False)
    outcome= Column(String, nullable=True)
    home_score= Column(Integer, default=0)
    away_score= Column(Integer, default=0)
    fixture_status= Column(Enum(FixtureStatus), defautl= FixtureStatus.future)

    league= relationship("League" , back_populates="fixtures")
    stakes = relationship('Stake', back_populates="match")