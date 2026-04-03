import enum
from turtle import home
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Enum, DateTime

from db.db_setup import Base
from db.models.mixins import TimeStamp
from pydantic_schemas.stake_schemas import StakeStatus, StakeWinner

class Stake(Base, TimeStamp):
    __tablename__ = "stakes"

    id= Column(Integer, primary_key=True, nullable=False, index=True)
    user_id= Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id= Column(Integer, ForeignKey("fixtures.local_id"), nullable=False)
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
    possibleWin= Column(Integer, nullable=True)
    public= Column(Boolean, nullable=True, default= False)

    user = relationship("User", back_populates='owned_stakes', foreign_keys=[user_id])
    invited_user = relationship("User", back_populates='invited_stakes', foreign_keys=[invited_user_id])
    match = relationship("Fixture", back_populates='stakes')



class PoolStakeStatus(str, enum.Enum):
    active = "active"
    locked = "locked"
    resolved = "resolved"
    # cancelled = "cancelled" # not important but just in case we need to use it in future 

class PoolStakeChoice(str, enum.Enum):
    home = "home"
    away = "away"
    draw = "draw" 

# notes: 
# - has no creator id since all the stakes are automatic and created by the system / house
# - this is different from uniques stakes which are created by users

class PoolStake(Base, TimeStamp):
    __tablename__ = "pool_stakes"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("fixtures.local_id"), nullable=True)
    league_id = Column(Integer, ForeignKey("leagues.local_id"), nullable=True)
    stake_id= Column(Integer, ForeignKey("stakes.id"), nullable=False) # can;t be nullable since these are unique and are tied ot the stakes that are actualy availabe in the system

    stake_status = Column(
        Enum(PoolStakeStatus),
        nullable=False,
        default=PoolStakeStatus.active
    )

    # timing
    locks_at = Column(DateTime, nullable=True) # this value will be tied to the start time of the match right -> for now we keep it such that once the match has started you cannot put you money in anymore.
    resolution_date = Column(DateTime, nullable=True) # the resulution datetime will be at about 1 minute after the match has ended , though I will try as much as to make it automatic so that so long as the match has ended payouts are done and the stake is resolved.

    # resolution
    # resolution_source = Column(String, nullable=True) no need for this since we will be using the outcome to determine the winner
    # to avoid writing alot of code we will just resuse the normal stakes resolution for this , so this stake has to point to the stakes model so that we can pull the outcome data from the actual stake
    outcome = Column(Enum(PoolStakeChoice), nullable=True) # I think we should do away with this and source outcome data from the stakes model

    # pool tracking — updated on every new entry
    pool_amount = Column(Integer, nullable=False, default=0)
    home_pool = Column(Integer, nullable=False, default=0)
    away_pool = Column(Integer, nullable=False, default=0)
    draw_pool = Column(Integer, nullable=False, default=0) # for non-match stakes where a draw pool is not necesary eg: will ruto win the presidecy ? 

    # participant tracking — updated on every new entry
    home_pool_count = Column(Integer, nullable=False, default=0)
    away_pool_count = Column(Integer, nullable=False, default=0)
    draw_pool_count = Column(Integer, nullable=False, default=0)

    # relationships
    poolstakeentries = relationship("PoolStakeEntry", back_populates="pool_stake")
    match = relationship("Fixture", back_populates="pool_stakes", foreign_keys=[match_id])
    league = relationship("League", back_populates="pool_stakes", foreign_keys=[league_id])


class PoolStakeEntry(Base, TimeStamp):
    __tablename__ = "pool_stake_entries"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    pool_stake_id = Column(
        Integer,
        ForeignKey("pool_stakes.id"),
        nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    placement = Column(Enum(PoolStakeChoice), nullable=False)
    amount = Column(Integer, nullable=False)
    payout_amount = Column(Integer, nullable=True)  # written at resolution
    possible_win = Column(Integer, nullable=True)  # I need to this to change with every entry onto the stake

    # relationships
    pool_stake = relationship("PoolStake", back_populates="poolstakeentries")
    user = relationship("User", foreign_keys=[user_id])