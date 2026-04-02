from sqlalchemy import Column, Integer
from db.db_setup import Base
from db.models.mixins import TimeStamp

class UniqueStake(Base, TimeStamp):
    __tablename__ = "unique_stakes"

    id= Column(Integer, primary_key=True, nullable=False, index=True)
    