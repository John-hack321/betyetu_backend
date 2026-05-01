import enum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Enum as SAEnum, Boolean, Text, column
)

from sqlalchemy.orm import relationship
from db.db_setup import Base
from db.models.mixins import TimeStamp


class PredictionMarketStatus(str, enum.Enum):
    pending_approval = "pending_approval"   # user submitted, waiting for admin
    active            = "active"            # trading is open
    locked            = "locked"            # trading closed, awaiting resolution
    resolved          = "resolved"          # admin has set the outcome
    rejected          = "rejected"          # admin rejected the proposal
    cancelled         = "cancelled"         # cancelled before any trades


class PredictionMarketOutcome(str, enum.Enum):
    yes = "yes"
    no  = "no"


class PredictionTradeType(str, enum.Enum):
    buy  = "buy"
    sell = "sell"


class PredictionPositionStatus(str, enum.Enum):
    open   = "open"    # user still holds the shares
    closed = "closed"  # user sold back all shares
    settled = "settled" # market resolved, payout processed


# Models 

# we need this one for grouping of pred markets
class PredictionMarketGroup(Base, TimeStamp):
    __tablename__ = "prediction_market_groups"
    
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    question = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    featured = Column(Boolean, nullable=False, default=False) # to allow for easier handling of the data i the frontend
    resolved = Column(Boolean, nullable=False, default=False) # to know if the binary sub markets have already been fully closed

    # this will be updated everytime a user buys / sells on the binary sub markets involved
    total_collected = Column(Float, nullable=False, default=0.0) # to track the total amount collected from users onto the binary sub markets
    locks_at = Column(DateTime, nullable=False) # when the market locks for trading
    resolution_date = Column(DateTime, nullable=False) # when the market resolves
    resolution_source = Column(String, nullable=False) # where the resolution came from (e.g. "official", "user_reported", etc.)

    # relationships
    markets = relationship("PredictionMarket", back_populates="market_group")

class PredictionMarket(Base, TimeStamp):
    """  I thought I'd leave these explanations here so that anyone reading this codebase wouldn;t be confused
    The core market object.

    Design decisions:
    - q_yes / q_no are stored as floats (shares, not KES).
        They represent the total shares issued on each side.
    - b is set at market creation and never changes during trading.
        (Changing b mid-market shifts prices for all existing holders.)
    - The house seeds each market by holding b * ln(2) KES in reserve.
        This is tracked via the `house_reserve` column.
    - resolution is manual — admin sets `outcome` via the admin dashboard.
    - `creator_id` is nullable because admins can create markets too.
    """
    __tablename__ = "prediction_markets"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    market_group_id = Column(Integer, ForeignKey("prediction_market_groups.id"), nullable=True) # nullable since not all markets will belong to a group
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True) # who proposed the mkt ( admin or a user ) , for admin this fild is null
    question = Column(String, nullable=False) # the qn the mkt is about
    description = Column(Text, nullable=True) # a longer descriptoin of the mkt but this is optional.
    category = Column(String, nullable=True) # eg. sports and I think we should make it an enum as early as possible: for now its just a string
    option = Column(String, nullable=True)

    # LMSR state 
    b = Column(Float, nullable=False, default=1000.0) # constrols the volatility of the market, the smaller the b the higher the volatility

    # Total shares issued on each side. Start at 0.
    q_yes = Column(Float, nullable=False, default=0.0)
    q_no  = Column(Float, nullable=False, default=0.0)

    # Total KES collected from all trades (this is what the house holds)
    total_collected = Column(Float, nullable=False, default=0.0)

    # The reserve the house must hold: b * ln(2)
    # Set at market creation. Used for financial reporting.
    house_reserve = Column(Float, nullable=False, default=0.0)

    #  Lifecycle => mkt lifecylce from creation / proposal to resolution by the admins
    market_status = Column(SAEnum(PredictionMarketStatus),
        nullable=False,
        default=PredictionMarketStatus.pending_approval
    )

    locks_at = Column(DateTime, nullable=True) # shows when tradin will end and the market will lock

    # Resolution date (informational — not enforced by code)
    resolution_date = Column(DateTime, nullable=True)

    # The source admin will use to verify the resolution
    resolution_source = Column(String, nullable=True)

    # Resolution 
    # Set by admin when resolving
    outcome = Column(SAEnum(PredictionMarketOutcome), nullable=True)

    # Admin notes shown publicly after resolution
    outcome_notes = Column(Text, nullable=True)

    # Admin notes shown only to creator (e.g. why market was rejected)
    admin_notes = Column(Text, nullable=True)
    featured = Column(Boolean, default=False, nullable= True) # for now we need the nullability since we already have tables created in the system

    creator  = relationship("User", foreign_keys=[creator_id])
    trades   = relationship("PredictionMarketTrade", back_populates="market")
    positions = relationship("PredictionMarketPosition", back_populates="market")
    market_group = relationship("PredictionMarketGroup", foreign_keys=[market_group_id])


class PredictionMarketPosition(Base, TimeStamp):
    """
    Tracks what a user currently holds in a market.

    A user can hold YES shares, NO shares, or both (if they bought on
    different sides at different times).  In practice, most users will
    only hold one side — but the model supports both.

    When a user buys more shares, their existing position for that side is
    updated (shares_held increases, average_cost updates).
    When they sell, shares_held decreases.
    When the market resolves, settled_payout is written and status → settled.
    """
    __tablename__ = "prediction_market_positions"

    id = Column(Integer, primary_key=True, nullable=False, index=True)

    market_id = Column(Integer,ForeignKey("prediction_markets.id"),nullable=False,index=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False,index=True)

    # "yes" or "no"
    side = Column(SAEnum(PredictionMarketOutcome), nullable=False)

    # How many shares the user currently holds on this side
    shares_held = Column(Float, nullable=False, default=0.0)

    # Total KES spent to acquire the current position
    # Used to calculate profit/loss when the user sells or market resolves
    total_cost = Column(Float, nullable=False, default=0.0)

    # Derived: total_cost / shares_held at time of last purchase
    # Stored for convenience (so you don't have to recalculate it from trades)
    average_cost_per_share = Column(Float, nullable=False, default=0.0)

    # Position lifecycle
    position_status = Column(
        SAEnum(PredictionPositionStatus),
        nullable=False,
        default=PredictionPositionStatus.open
    )

    # Written at resolution: how much this position paid out
    settled_payout = Column(Float, nullable=True)

    market = relationship("PredictionMarket", back_populates="positions")
    user   = relationship("User", foreign_keys=[user_id])


class PredictionMarketTrade(Base, TimeStamp):
    """
    Immutable ledger entry for every buy and sell.

    Every time a user buys or sells shares, we write one row here.
    This allows us to have : 
    - A full audit trail for financial reconciliation
    - Price history for the frontend chart
    - Debugging tool when prices seem wrong

    Never update or delete these rows. If a trade was made in error,
    write a correcting trade (a sell of the same amount).
    """
    __tablename__ = "prediction_market_trades"

    id = Column(Integer, primary_key=True, nullable=False, index=True)

    market_id = Column(Integer,ForeignKey("prediction_markets.id"),nullable=False,index=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False,index=True)

    # "buy" or "sell"
    trade_type = Column(SAEnum(PredictionTradeType), nullable=False)

    # "yes" or "no"
    side = Column(SAEnum(PredictionMarketOutcome), nullable=False)

    # How many shares were bought / sold in this trade
    shares = Column(Float, nullable=False)

    # KES paid (buy) or received (sell)
    kes_amount = Column(Float, nullable=False)

    # The YES price at the moment of this trade (for charting)
    yes_price_at_trade = Column(Float, nullable=False)

    # Market state after this trade (for debugging / rollback)
    q_yes_after = Column(Float, nullable=False)
    q_no_after  = Column(Float, nullable=False)

    market = relationship("PredictionMarket", back_populates="trades")
    user   = relationship("User", foreign_keys=[user_id])