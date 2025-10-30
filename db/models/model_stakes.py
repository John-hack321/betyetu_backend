import enum
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Enum

from db.db_setup import Base
from db.models.mixins import TimeStamp

# Define enums for database use
class StakeWinner(enum.Enum):
    owner = 1
    guest = 2

class StakeStatus(enum.Enum):
    successfull = 1
    pending = 0

class Stake(Base, TimeStamp):
    __tablename__ = "stakes"

    id= Column(Integer, primary_key=True, nullable=False, index=True)
    user_id= Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id= Column(Integer, ForeignKey("fixtures.match_id"), nullable=False, name="match_id")
    home= Column(String, nullable=False)
    away= Column(String, nullable=False)
    placement= Column(String, nullable=False)
    amount= Column(Integer, nullable=True)
    invited_user_id= Column(Integer, ForeignKey("users.id"), nullable=True)
    invited_user_placement= Column(String, nullable=True)
    invited_user_amount= Column(Integer, nullable=True)
    invite_code= Column(String, nullable=False)
    stake_status= Column(Enum(StakeStatus), nullable=False, default=StakeStatus.pending)
    winner= Column(Enum(StakeWinner), nullable=True)

    user = relationship("User", back_populates='stakes_owned', foreign_keys=[user_id])
    invited_user = relationship("User", back_populates='stakes_invited', foreign_keys=[invited_user_id])
    match = relationship("Fixture", back_populates='stakes')