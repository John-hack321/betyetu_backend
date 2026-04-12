from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MarketSide(str, Enum):
    yes = "yes"
    no  = "no"


# Request payloads 

class CreateMarketPayload(BaseModel):
    """User submits a market proposal.  Admin approves before it goes live."""
    question: str = Field(..., min_length=10, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    resolution_source: Optional[str] = None
    locks_at: Optional[datetime] = None
    resolution_date: Optional[datetime] = None


class AdminCreateMarketPayload(CreateMarketPayload):
    """Admin can also set b and go straight to active."""
    b: float = Field(default=1000.0, ge=100.0, le=1_000_000.0)
    go_live_immediately: bool = False


class BuySharesPayload(BaseModel):
    market_id: int
    side: MarketSide
    shares: float = Field(..., gt=0)


class SellSharesPayload(BaseModel):
    market_id: int
    side: MarketSide
    shares: float = Field(..., gt=0)


class AdminResolveMarketPayload(BaseModel):
    market_id: int
    outcome: MarketSide
    outcome_notes: Optional[str] = None


class AdminApproveMarketPayload(BaseModel):
    market_id: int
    b: float = Field(default=1000.0, ge=100.0, le=1_000_000.0)
    admin_notes: Optional[str] = None


#  Response objects 

class MarketPricesResponse(BaseModel):
    yes_price: float
    no_price: float


class BuyQuoteResponse(BaseModel):
    """
    Preview shown to user BEFORE they confirm a buy:
    "For X shares you will pay Y KES"
    """
    market_id: int
    side: MarketSide
    shares: float
    cost_kes: float
    yes_price_after: float   # what price will be after this trade goes through
    no_price_after: float


class SellQuoteResponse(BaseModel):
    """Preview shown before a sell confirmation."""
    market_id: int
    side: MarketSide
    shares: float
    payout_kes: float
    yes_price_after: float
    no_price_after: float


class MarketSummaryResponse(BaseModel):
    id: int
    question: str
    description: Optional[str]
    category: Optional[str]
    market_status: str
    yes_price: float
    no_price: float
    total_collected: float
    locks_at: Optional[datetime]
    resolution_date: Optional[datetime]
    outcome: Optional[str]

    class Config:
        from_attributes = True


class UserPositionResponse(BaseModel):
    market_id: int
    question: str
    side: str
    shares_held: float
    total_cost: float
    average_cost_per_share: float
    current_value: float          # shares_held * current_price_for_side
    unrealised_pnl: float         # current_value - total_cost
    position_status: str
    settled_payout: Optional[float]

    class Config:
        from_attributes = True


class TradeConfirmationResponse(BaseModel):
    trade_id: int
    market_id: int
    side: str
    trade_type: str
    shares: float
    kes_amount: float
    yes_price_after: float
    no_price_after: float
    new_account_balance: float

class AdminCreateGroupMarketPayload(BaseModel):
    group_market_question: str
    group_market_description: str
    locks_at: datetime
    resolution_date: datetime
    resolution_source: str
    submarket_entries: list[str]
    b: float = Field(default=1000.0, ge=100.0, le=1_000_000.0)
    category: str
    go_live_immediately: bool = False

class AdminCreateFixturePredictionMarket(BaseModel):
    fixture_id: int
    locks_at: datetime
    resolution_date: datetime
    resolution_source: str
    b: float = Field(default=1000.0, ge=100.0, le=1_000_000.0)
    category: str
    go_live_immediately: bool = False