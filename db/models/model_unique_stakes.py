import enum
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from db.db_setup import Base
from db.models.mixins import TimeStamp


class UniqueStakeStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    active = "active"
    locked = "locked"
    resolved = "resolved"
    rejected = "rejected"
    cancelled = "cancelled"


class UniqueStakeChoice(str, enum.Enum):
    yes = "yes"
    no = "no"
    draw = "draw"  # only valid for match-based stakes


class UniqueStakeType(str, enum.Enum):
    match_based = "match_based"
    event_based = "event_based"


class UniqueStakeEntryStatus(str, enum.Enum):
    active = "active"
    refunded = "refunded"


class UniqueStake(Base, TimeStamp):
    __tablename__ = "unique_stakes"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("fixtures.local_id"), nullable=True)
    league_id = Column(Integer, ForeignKey("leagues.local_id"), nullable=True)

    stake_statement = Column(String, nullable=False)
    stake_type = Column(SAEnum(UniqueStakeType), nullable=False)
    stake_status = Column(
        SAEnum(UniqueStakeStatus),
        nullable=False,
        default=UniqueStakeStatus.pending_approval
    )

    # timing
    locks_at = Column(DateTime, nullable=True)
    resolution_date = Column(DateTime, nullable=True)

    # resolution
    resolution_source = Column(String, nullable=True)
    outcome = Column(SAEnum(UniqueStakeChoice), nullable=True)
    outcome_notes = Column(String, nullable=True)
    admin_notes = Column(String, nullable=True)  # shown to creator on rejection

    # pool tracking — updated on every new entry
    pool_amount = Column(Integer, nullable=False, default=0)
    yes_pool = Column(Integer, nullable=False, default=0)
    no_pool = Column(Integer, nullable=False, default=0)
    draw_pool = Column(Integer, nullable=True, default=0) # for non-match stakes where a draw pool is not necesary eg: will ruto win the presidecy ? 

    # participant tracking — updated on every new entry
    yes_count = Column(Integer, nullable=False, default=0)
    no_count = Column(Integer, nullable=False, default=0)
    draw_count = Column(Integer, nullable=True, default=0) # has to be nullable since the draw pool is also nullable
    # relationships
    creator = relationship("User", foreign_keys=[creator_id])
    entries = relationship("UniqueStakeEntry", back_populates="unique_stake")
    match = relationship("Fixture", back_populates="unique_stakes", foreign_keys=[match_id])
    league = relationship("League", back_populates="unique_stakes", foreign_keys=[league_id])


class UniqueStakeEntry(Base, TimeStamp):
    __tablename__ = "unique_stake_entries"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    unique_stake_id = Column(
        Integer,
        ForeignKey("unique_stakes.id"),
        nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    placement = Column(SAEnum(UniqueStakeChoice), nullable=False)
    amount = Column(Integer, nullable=False)
    payout_amount = Column(Integer, nullable=True)  # written at resolution
    status = Column(
        SAEnum(UniqueStakeEntryStatus),
        nullable=False,
        default=UniqueStakeEntryStatus.active
    )

    # relationships
    unique_stake = relationship("UniqueStake", back_populates="entries")
    user = relationship("User", foreign_keys=[user_id])