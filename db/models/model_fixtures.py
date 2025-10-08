import datetime
from db.db_setup import Base
from db.models.mixins import TimeStamp

from sqlalchemy import String , Integer , ForeignKey , Text , DateTime , Boolean
from sqlalchemy.orm import relationship

class Fixture(Base , TimeStamp):
    __tablename__ = "fixtures"

    match_id= Column(Integer, nullable=False, primary_key=True)
    home_team_id= Column(Integer, nullable=False)
    home_team= Column(String, nullable=False)
    away_team_id= column(Integer, nullable=False)
    away_team= column(String, nullable=False)
    match_date= Column(DateTime, nullable=False)
    is_played= Column(Boolean, nullable=False, default=False)
    outcome= Column(String, nullabe=True)
    home_score= Column(String, default='0')
    away_score= Column(String, default='0')