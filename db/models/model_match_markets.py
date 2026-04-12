import enum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Enum as SAEnum, Boolean, Text
)
from sqlalchemy.orm import relationship
from db.db_setup import Base
from db.models.mixins import TimeStamp
from db.models.model_prediction_market import PredictionMarketStatus

# NOTE: all the api endpoints relating to this model have all been defined on the general prediction market endpoint


# ── Enums ─────────────────────────────────────────────────────────────────────



class FixtureBasedMarketOutcome(str, enum.Enum):
    home = "home"
    draw = "draw"
    away = "away"


class FixtureBasedTradeType(str, enum.Enum):
    buy  = "buy"
    sell = "sell"


class FixtureBasedPositionStatus(str, enum.Enum):
    open    = "open"     # user still holds shares
    closed  = "closed"   # user sold all shares back
    settled = "settled"  # market resolved, payout processed


# ── Models ────────────────────────────────────────────────────────────────────

class FixtureBasedMarket(Base, TimeStamp):
    """
    A 3-outcome LMSR prediction market tied directly to a fixture.

    Works for any sport that uses a fixture model — football, basketball,
    rugby, or anything else — as long as the match has a home side, away
    side, and a draw is a valid result.

    Design notes:
    - fixture_id links to Fixture.local_id so we always know which match
      this market belongs to — home team, away team, date all come from there.
    - q_home, q_draw, q_away track total shares issued on each side.
      They all start at 0.0 when the market opens.
    - b controls liquidity / price sensitivity. Larger b = flatter price
      movement per trade. Smaller b = more volatile.
    - house_reserve = b * ln(3) — the amount the platform must seed per market
      as worst-case loss cover. Set at creation, never changes.
    - total_collected tracks total KES received from all buys (net of sells).
    - creator_id is nullable because admins can create markets too.
      For admin-created markets it will be None.
    - resolution is always manual — admin sets outcome via admin dashboard.
    """
    __tablename__ = "fixture_based_markets"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    fixture_id = Column(
        Integer,
        ForeignKey("fixtures.local_id"),
        nullable=False,
        index=True
    )
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    question = Column(String, nullable=False)   # e.g. "Who wins Arsenal vs Man City ? or Arsenal va Man City "  we will decide on the best format later
    description = Column(Text,   nullable=True)
    category = Column(String, nullable=True)    # e.g. will aways be sports , we will implement further sorting later on

    # LMSR state — all three quantities start at 0
    b = Column(Float, nullable=False, default=1000.0)
    q_home = Column(Float, nullable=False, default=0.0)
    q_draw = Column(Float, nullable=False, default=0.0)
    q_away = Column(Float, nullable=False, default=0.0)

    # Financials
    total_collected = Column(Float, nullable=False, default=0.0)
    house_reserve   = Column(Float, nullable=False, default=0.0)  # b * ln(3)

    # Lifecycle
    market_status = Column(
        SAEnum(PredictionMarketStatus),
        nullable=False,
        default=PredictionMarketStatus.pending_approval,
    )
    locks_at = Column(DateTime, nullable=True)  # when trading closes
    resolution_date = Column(DateTime, nullable=True)  # informational only
    resolution_source = Column(String,   nullable=True)  # e.g. "BBC Sport", "official"

    # Resolution — written by admin
    outcome = Column(SAEnum(FixtureBasedMarketOutcome), nullable=True)
    outcome_notes = Column(Text, nullable=True)  # public note after resolution
    admin_notes = Column(Text, nullable=True)  # private note to creator on rejection

    featured = Column(Boolean, default=False, nullable=True)

    # Relationships
    fixture = relationship("Fixture",  foreign_keys=[fixture_id], uselist=False)
    creator = relationship("User",     foreign_keys=[creator_id])
    trades  = relationship("FixtureBasedMarketTrade",    back_populates="market")
    positions = relationship("FixtureBasedMarketPosition", back_populates="market")


class FixtureBasedMarketPosition(Base, TimeStamp):
    """
    Tracks what a single user currently holds in a FixtureBasedMarket.

    A user can hold shares on any one of the three sides.
    If they buy on multiple sides (unusual but valid), a separate position
    row is created per side — same pattern as the binary PredictionMarketPosition.

    shares_held decreases on sell, increases on additional buys.
    At resolution: settled_payout is written and position_status → settled.
    Losing positions also get settled with settled_payout = 0.
    """
    __tablename__ = "fixture_based_market_positions"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("fixture_based_markets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # "home", "draw", or "away"
    side = Column(SAEnum(FixtureBasedMarketOutcome), nullable=False)

    # Share accounting
    shares_held = Column(Float, nullable=False, default=0.0)
    total_cost  = Column(Float, nullable=False, default=0.0)  # total KES spent (base cost, excl fee)
    average_cost_per_share = Column(Float, nullable=False, default=0.0)  # total_cost / shares_held at last buy

    # Lifecycle
    position_status = Column(
        SAEnum(FixtureBasedPositionStatus),
        nullable=False,
        default=FixtureBasedPositionStatus.open,
    )
    settled_payout = Column(Float, nullable=True)  # written at resolution

    # Relationships
    market = relationship("FixtureBasedMarket", back_populates="positions")
    user   = relationship("User", foreign_keys=[user_id])


class FixtureBasedMarketTrade(Base, TimeStamp):
    """
    Immutable ledger entry for every buy and sell on a FixtureBasedMarket.

    Never update or delete these rows.
    Used for:
    - Full audit trail for financial reconciliation
    - Price history for the frontend chart (all three prices stored per trade)
    - Debugging when prices seem off

    home_price_at_trade: the implied P(home) probability at the moment of the trade.
    q_home_after, q_draw_after, q_away_after: full market state snapshot after trade.
    """
    __tablename__ = "fixture_based_market_trades"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    market_id = Column(Integer, ForeignKey("fixture_based_markets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),                 nullable=False, index=True)

    trade_type = Column(SAEnum(FixtureBasedTradeType),    nullable=False)  # "buy" or "sell"
    side = Column(SAEnum(FixtureBasedMarketOutcome), nullable=False)  # "home", "draw", or "away"

    shares = Column(Float, nullable=False)  # shares bought or sold in this trade
    kes_amount = Column(Float, nullable=False)  # KES paid (buy) or received net of fee (sell)

    # All three prices stored at trade time so the frontend chart can render
    # all three probability lines without recalculating anything
    home_price_at_trade = Column(Float, nullable=False)
    draw_price_at_trade = Column(Float, nullable=False)
    away_price_at_trade = Column(Float, nullable=False)

    # Full market state after this trade — for debugging and rollback analysis
    q_home_after = Column(Float, nullable=False)
    q_draw_after = Column(Float, nullable=False)
    q_away_after = Column(Float, nullable=False)

    # Relationships
    market = relationship("FixtureBasedMarket", back_populates="trades")
    user = relationship("User", foreign_keys=[user_id])