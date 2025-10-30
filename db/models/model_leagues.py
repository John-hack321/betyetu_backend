from asyncio import mixins
from sqlalchemy.orm import relationship
from sqlalchemy import Column , String , Integer , Enum , Boolean , ForeignKey , Text

from db.db_setup import Base
from db.models.mixins import TimeStamp

class League(TimeStamp , Base):
    __tablename__ = "leagues"

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)

    fixtures= relationship('Fixture', back_populates="league") # this is a one to many relationship so there is no need of setting uselist to false

class PopularLeague(TimeStamp , Base):
    __tablename__ = "popular_leagues"

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)