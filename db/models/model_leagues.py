from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship

from db.db_setup import Base
from db.models.mixins import TimeStamp

class League(TimeStamp, Base):
    __tablename__ = "leagues"

    local_id= Column(Integer, nullable=False, primary_key=True)
    id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)

    # Use string references
    fixtures= relationship("Fixture", back_populates="league")
    teams= relationship("Team", back_populates="league")

class PopularLeague(TimeStamp, Base):
    __tablename__ = "popular_leagues"

    local_id= Column(Integer, nullable=False, primary_key=True)
    id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    localized_name = Column(String, nullable=False)
    logo_url = Column(String, nullable=False)
    fixture_added = Column(Boolean, default=False)