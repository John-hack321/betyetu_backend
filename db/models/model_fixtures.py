from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Column, Enum
from sqlalchemy.orm import relationship
import enum

from db.db_setup import Base
from db.models.mixins import TimeStamp

class FixtureStatus(enum.Enum):
    live= "live"
    future= "future"
    expired= "expired"

class Fixture(Base, TimeStamp):
    __tablename__ = "fixtures"

    local_id= Column(Integer, nullable=False, primary_key=True)
    match_id= Column(Integer, nullable=True)
    league_id = Column(Integer, ForeignKey("leagues.local_id"), nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.local_id"), nullable=False)
    home_team_id= Column(Integer, nullable=False)
    home_team= Column(String, nullable=False)
    away_team_id= Column(Integer, nullable=False)
    away_team= Column(String, nullable=False)
    match_date= Column(DateTime, nullable=False)
    is_played= Column(Boolean, nullable=False, default=False)
    outcome= Column(String, nullable=True)
    home_score= Column(Integer, default=0)
    away_score= Column(Integer, default=0)
    fixture_status= Column(Enum(FixtureStatus), default=FixtureStatus.future)
    winner= Column(String, nullable=True)

    # Use string references for cross-file relationships
    league= relationship("League", back_populates="fixtures")
    stakes = relationship("Stake", back_populates="match")
    season= relationship("Season", back_populates="fixtures")