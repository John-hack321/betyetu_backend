from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Enum

from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.stake_schemas import StakeStatus, StakeWinner

class Stake(Base, TimeStamp):
    __tablename__ = "stakes"

    id= Column(Integer, primary_key=True, nullable=False, index=True)
    user_id= Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id= Column(Integer, ForeignKey("fixtures.id"),nullable=False)
    home= Column(String, nullable=False)
    away= Column(String, nullable=False)
    placement= Column(String, nullable=False)
    amount= Column(Integer, nullable=True)
    invited_user_id= Column(Integer, ForeignKey("users.id"), nullable=True)
    invited_user_placement= Column(String, nullable=True)
    invited_user_amount= Column(Integer, nullable=True)
    invite_code= Column(String, nullable=False)
    stake_status= Column(StakeStatus, nullable=False, default=StakeStatus.pending)
    winner= Column(StakeWinner, nullable=True)

    user= relationship("User", back_populates='stakes')
    invited_user= relationship("User", back_populates='stakes')
    match= relationship("Fixture", back_populates='stakes')