from asyncio import mixins
from sqlite3.dbapi2 import Timestamp
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text, false

from db.db_setup import Base
from db.models.mixins import TimeStamp


class League(TimeStamp , Base):
    __tablename__ = "leagues"

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)

class PopularLeague(Timestamp , Base):
    __tablename__ = "popular_leagues"

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)