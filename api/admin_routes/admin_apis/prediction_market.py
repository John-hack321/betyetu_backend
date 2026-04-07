from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.utils.dependancies import db_dependancy
from db.models.model_prediction_market import PredictionMarket
from db.models.model_prediction_market import PredictionMarketStatus

from services.market_Logic.trade_service import process_market_resolution
from pydantic_schemas.prediction_market_schemas import (
    AdminCreateMarketPayload,
    AdminApproveMarketPayload,
    AdminResolveMarketPayload,
)

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)


admin_router = APIRouter(
    prefix="/admin/prediction_markets",
    tags=["admin/prediction_markets"],
)


@admin_router.post("/create")
async def admin_create_market(
    payload: AdminCreateMarketPayload,
    db: db_dependancy,
):
    """Admin creates a market directly — skips pending_approval."""
    try:
        import math as _math
        reserve = payload.b * _math.log(2)

        new_market = PredictionMarket(
            creator_id=None,
            question=payload.question,
            description=payload.description,
            category=payload.category,
            resolution_source=payload.resolution_source,
            locks_at=payload.locks_at,
            resolution_date=payload.resolution_date,
            market_status=(
                PredictionMarketStatus.active
                if payload.go_live_immediately
                else PredictionMarketStatus.pending_approval
            ),
            b=payload.b,
            q_yes=0.0,
            q_no=0.0,
            total_collected=0.0,
            house_reserve=reserve,
        )

        # I know , I will create a utils files for the prediction markets for now just work with this.
        db.add(new_market)
        await db.commit()
        await db.refresh(new_market)

        return {
            "market_id": new_market.id,
            "status": new_market.market_status.value,
            "b": payload.b,
            "house_reserve": round(reserve, 2),
            "message": f"Market created. House reserve required: {reserve:.2f} KES",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Admin create market failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create market")


@admin_router.post("/approve")
async def admin_approve_market(
    payload: AdminApproveMarketPayload,
    db: db_dependancy,
):
    """Approve a pending market and set its b value."""
    try:
        import math as _math
        market = await db.get(PredictionMarket, payload.market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status != PredictionMarketStatus.pending_approval:
            raise HTTPException(
                status_code=400,
                detail=f"Market is {market.market_status.value}, not pending approval"
            )

        market.b             = payload.b
        market.house_reserve = payload.b * _math.log(2)
        market.market_status = PredictionMarketStatus.active
        market.admin_notes   = payload.admin_notes

        await db.commit()
        await db.refresh(market)

        return {
            "market_id": market.id,
            "status": "active",
            "b": market.b,
            "house_reserve": round(market.house_reserve, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Admin approve market failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve market")


@admin_router.post("/reject")
async def admin_reject_market(
    market_id: int,
    admin_notes: str,
    db: db_dependancy,
):
    try:
        market = await db.get(PredictionMarket, market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        market.market_status = PredictionMarketStatus.rejected
        market.admin_notes   = admin_notes

        await db.commit()
        return {"market_id": market_id, "status": "rejected"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Reject market failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject market")


@admin_router.post("/lock")
async def admin_lock_market(market_id: int, db: db_dependancy):
    """Lock trading on a market (no more buys/sells, awaiting resolution)."""
    try:
        market = await db.get(PredictionMarket, market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        market.market_status = PredictionMarketStatus.locked
        await db.commit()
        return {"market_id": market_id, "status": "locked"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to lock market")


@admin_router.post("/resolve")
async def admin_resolve_market(
    payload: AdminResolveMarketPayload,
    db: db_dependancy,
):
    """
    Resolve a market and pay out all winning positions.
    This is the most important admin action — it triggers all payouts.
    """
    try:
        result = await process_market_resolution(
            db=db,
            market_id=payload.market_id,
            outcome=payload.outcome.value,
            outcome_notes=payload.outcome_notes,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve market failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resolve market")


@admin_router.get("/pending")
async def admin_get_pending_markets(db: db_dependancy):
    """Get all markets waiting for approval."""
    try:
        result = await db.execute(
            select(PredictionMarket)
            .where(PredictionMarket.market_status == PredictionMarketStatus.pending_approval)
            .order_by(PredictionMarket.created_at.asc())
        )
        markets = result.scalars().all()

        return [
            {
                "id": m.id,
                "question": m.question,
                "description": m.description,
                "category": m.category,
                "creator_id": m.creator_id,
                "resolution_source": m.resolution_source,
                "created_at": m.created_at,
            }
            for m in markets
        ]

    except Exception as e:
        logger.error(f"Get pending markets failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch pending markets")
