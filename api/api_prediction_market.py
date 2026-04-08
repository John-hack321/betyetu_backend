import math
import logging
from typing import List
import sys

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.dependancies import db_dependancy, user_dependancy
from db.models.model_prediction_market import (
    PredictionMarket,
    PredictionMarketPosition,
    PredictionMarketTrade,
    PredictionMarketStatus,
    PredictionMarketOutcome,
    PredictionPositionStatus,
)
from db.models.model_users import Account
from pydantic_schemas.prediction_market_schemas import (
    CreateMarketPayload,
    BuySharesPayload,
    SellSharesPayload,
    BuyQuoteResponse,
    SellQuoteResponse,
    MarketSummaryResponse,
    UserPositionResponse,
    TradeConfirmationResponse,
)
from services.market_Logic.LMSR import (
    yes_price,
    cost_to_buy,
    payout_from_sell,
    shares_for_budget,
    max_house_loss,
)
from services.market_Logic.trade_service  import (
    process_buy,
    process_sell,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/prediction_markets",
    tags=["prediction_markets"],
)


@router.get("/")
async def get_active_markets(
    db: db_dependancy,
    user: user_dependancy,
    page: int = 1,
    limit: int = 50,
    category: str = None,
):
    """
    Get all active prediction markets.
    Returns current prices for each market.
    """
    try:
        offset = (page - 1) * limit

        query = (
            select(PredictionMarket)
            .where(PredictionMarket.market_status == PredictionMarketStatus.active)
        )

        if category:
            query = query.where(PredictionMarket.category == category)

        total = await db.scalar(
            select(func.count())
            .select_from(PredictionMarket)
            .where(PredictionMarket.market_status == PredictionMarketStatus.active)
        )

        result = await db.execute(
            query.order_by(PredictionMarket.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        markets = result.scalars().all()

        # Attach current prices to each market
        markets_with_prices = []
        for m in markets:
            p_yes = yes_price(m.q_yes, m.q_no, m.b)
            markets_with_prices.append({
                "id": m.id,
                "question": m.question,
                "description": m.description,
                "category": m.category,
                "market_status": m.market_status.value,
                "yes_price": round(p_yes, 4),
                "no_price": round(1.0 - p_yes, 4),
                "total_collected": m.total_collected,
                "locks_at": m.locks_at,
                "resolution_date": m.resolution_date,
                "outcome": m.outcome.value if m.outcome else None,
            })

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": math.ceil(total / limit),
            "has_next_page": (page * limit) < total,
            "data": markets_with_prices,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prediction markets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch markets")


@router.get("/{market_id}")
async def get_market_detail(
    market_id: int,
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Get full detail for one market including price history summary.
    """
    try:
        market = await db.get(PredictionMarket, market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        p_yes = yes_price(market.q_yes, market.q_no, market.b)

        # Get trade count for activity indicator
        trade_count = await db.scalar(
            select(func.count())
            .select_from(PredictionMarketTrade)
            .where(PredictionMarketTrade.market_id == market_id)
        )

        return {
            "id": market.id,
            "question": market.question,
            "description": market.description,
            "category": market.category,
            "market_status": market.market_status.value,
            "yes_price": round(p_yes, 6),
            "no_price": round(1.0 - p_yes, 6),
            "yes_shares_issued": market.q_yes,
            "no_shares_issued": market.q_no,
            "total_collected": market.total_collected,
            "trade_count": trade_count,
            "locks_at": market.locks_at,
            "resolution_date": market.resolution_date,
            "resolution_source": market.resolution_source,
            "outcome": market.outcome.value if market.outcome else None,
            "outcome_notes": market.outcome_notes,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market {market_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch market detail")


@router.get("/{market_id}/price_history")
async def get_price_history(
    market_id: int,
    db: db_dependancy,
    user: user_dependancy,
    limit: int = 100,
):
    """
    Returns the YES price at each trade — used to draw the price chart on the frontend.
    """
    try:
        result = await db.execute(
            select(
                PredictionMarketTrade.created_at,
                PredictionMarketTrade.yes_price_at_trade,
                PredictionMarketTrade.trade_type,
                PredictionMarketTrade.side,
            )
            .where(PredictionMarketTrade.market_id == market_id)
            .order_by(PredictionMarketTrade.created_at.asc())
            .limit(limit)
        )
        rows = result.all()

        return [
            {
                "timestamp": row.created_at,
                "yes_price": round(row.yes_price_at_trade, 6),
                "no_price": round(1.0 - row.yes_price_at_trade, 6),
                "trade_type": row.trade_type.value,
                "side": row.side.value,
            }
            for row in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Price history error market {market_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch price history")


@router.get("/{market_id}/quote/buy")
async def get_buy_quote(
    market_id: int,
    side: str,
    shares: float,
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Preview: "How much will X shares on side Y cost me?"
    Call this to show the user a price BEFORE they confirm.
    No money moves, no DB writes.
    """
    try:
        if side not in ("yes", "no"):
            raise HTTPException(status_code=400, detail="side must be 'yes' or 'no'")
        if shares <= 0:
            raise HTTPException(status_code=400, detail="shares must be positive")

        market = await db.get(PredictionMarket, market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status != PredictionMarketStatus.active:
            raise HTTPException(status_code=423, detail="Market is not active")

        cost = cost_to_buy(market.q_yes, market.q_no, market.b, shares, side)
        fee  = cost * 0.02
        total = cost + fee

        # Simulate price after trade
        sim_q_yes = market.q_yes + shares if side == "yes" else market.q_yes
        sim_q_no  = market.q_no  + shares if side == "no"  else market.q_no
        p_yes_after = yes_price(sim_q_yes, sim_q_no, market.b)

        return BuyQuoteResponse(
            market_id=market_id,
            side=side,
            shares=shares,
            cost_kes=round(total, 2),
            yes_price_after=round(p_yes_after, 6),
            no_price_after=round(1.0 - p_yes_after, 6),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Buy quote error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate buy quote")


@router.get("/{market_id}/quote/sell")
async def get_sell_quote(
    market_id: int,
    side: str,
    shares: float,
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Preview: "How much will I get for selling X shares on side Y?"
    """
    try:
        if side not in ("yes", "no"):
            raise HTTPException(status_code=400, detail="side must be 'yes' or 'no'")

        market = await db.get(PredictionMarket, market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        payout = payout_from_sell(market.q_yes, market.q_no, market.b, shares, side)
        fee    = payout * 0.02
        net    = payout - fee

        sim_q_yes = market.q_yes - shares if side == "yes" else market.q_yes
        sim_q_no  = market.q_no  - shares if side == "no"  else market.q_no
        p_yes_after = yes_price(max(sim_q_yes, 0), max(sim_q_no, 0), market.b)

        return SellQuoteResponse(
            market_id=market_id,
            side=side,
            shares=shares,
            payout_kes=round(net, 2),
            yes_price_after=round(p_yes_after, 6),
            no_price_after=round(1.0 - p_yes_after, 6),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sell quote error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate sell quote")


@router.post("/buy")
async def buy_shares(
    payload: BuySharesPayload,
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Execute a buy. Money moves, q values update, position is created/updated.
    """
    try:
        result = await process_buy(
            db=db,
            market_id=payload.market_id,
            user_id=user.get("user_id"),
            side=payload.side.value,
            shares=payload.shares,
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Buy failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Trade failed, please try again")


@router.post("/sell")
async def sell_shares(
    payload: SellSharesPayload,
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Execute a sell (exit the market).  Net payout credited to user's account.
    """
    try:
        result = await process_sell(
            db=db,
            market_id=payload.market_id,
            user_id=user.get("user_id"),
            side=payload.side.value,
            shares=payload.shares,
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sell failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Trade failed, please try again")

@router.post("/propose")
async def propose_market(
    payload: CreateMarketPayload,
    db: db_dependancy,
    user: user_dependancy,
):
    try:
        locks_at = payload.locks_at.replace(tzinfo=None) if payload.locks_at else None
        resolution_date = payload.resolution_date.replace(tzinfo=None) if payload.resolution_date else None

        new_market = PredictionMarket(
            creator_id=user.get("user_id"),
            question=payload.question,
            description=payload.description,
            category=payload.category,
            resolution_source=payload.resolution_source,
            locks_at=locks_at,
            resolution_date=resolution_date,
            market_status=PredictionMarketStatus.pending_approval,
            b=1000.0,
            q_yes=0.0,
            q_no=0.0,
            total_collected=0.0,
            house_reserve=0.0,
        )
        db.add(new_market)
        await db.commit()
        await db.refresh(new_market)

        return {
            "market_id": new_market.id,
            "status": "pending_approval",
            "message": "Your market has been submitted for review.",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Market proposal failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit market proposal")

@router.get("/my/positions")
async def get_my_positions(
    db: db_dependancy,
    user: user_dependancy,
):
    """
    Returns all of the user's open positions with current value and P&L.
    """
    try:
        result = await db.execute(
            select(PredictionMarketPosition, PredictionMarket)
            .join(PredictionMarket, PredictionMarketPosition.market_id == PredictionMarket.id)
            .where(
                PredictionMarketPosition.user_id == user.get("user_id"),
                PredictionMarketPosition.position_status.in_([
                    PredictionPositionStatus.open,
                    PredictionPositionStatus.settled,
                ]),
            )
            .order_by(PredictionMarketPosition.created_at.desc())
        )
        rows = result.all()

        positions = []
        for pos, market in rows:
            # Current price for this side
            p_yes = yes_price(market.q_yes, market.q_no, market.b)
            current_price = p_yes if pos.side == PredictionMarketOutcome.yes else (1.0 - p_yes)
            current_value = pos.shares_held * current_price
            unrealised_pnl = current_value - pos.total_cost

            positions.append({
                "market_id": market.id,
                "question": market.question,
                "market_status": market.market_status.value,
                "side": pos.side.value,
                "shares_held": pos.shares_held,
                "total_cost": round(pos.total_cost, 2),
                "average_cost_per_share": round(pos.average_cost_per_share, 4),
                "current_price": round(current_price, 6),
                "current_value": round(current_value, 2),
                "unrealised_pnl": round(unrealised_pnl, 2),
                "position_status": pos.position_status.value,
                "settled_payout": pos.settled_payout,
            })

        return positions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get positions error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch positions")