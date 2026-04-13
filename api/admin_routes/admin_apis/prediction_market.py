from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.utils.dependancies import db_dependancy
from db.models.model_match_markets import FixtureBasedMarket
from db.models.model_prediction_market import PredictionMarket
from db.models.model_prediction_market import PredictionMarketStatus
from db.models.model_prediction_market import PredictionMarketGroup
from db.models.model_fixtures import Fixture

from services.market_Logic.trade_service import process_market_resolution
from pydantic_schemas.prediction_market_schemas import (
    AdminCreateMarketPayload,
    AdminApproveMarketPayload,
    AdminResolveMarketPayload,
    AdminCreateGroupMarketPayload,
    AdminCreateFixturePredictionMarket
)

import logging
import sys
import math as _math


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

# NOTE: for the prediction markets we put it all in one file so there is no util for db operations everything is done here on this one file

@admin_router.post("/create")
async def admin_create_market(
    payload: AdminCreateMarketPayload,
    db: db_dependancy,
):
    """Admin creates a market directly — skips pending_approval."""
    try:
        reserve = payload.b * _math.log(2)

        # Strip timezone info before storing — DB uses TIMESTAMP WITHOUT TIME ZONE
        locks_at = payload.locks_at.replace(tzinfo=None) if payload.locks_at else None
        resolution_date = payload.resolution_date.replace(tzinfo=None) if payload.resolution_date else None

        new_market = PredictionMarket(
            creator_id=None,
            question=payload.question,
            description=payload.description,
            category=payload.category,
            resolution_source=payload.resolution_source,
            locks_at=locks_at,
            resolution_date=resolution_date,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to fetch pending markets: {str(e)}")

@admin_router.post("/create_group_market")
async def admin_create_group_market(
    db: db_dependancy,
    payload: AdminCreateGroupMarketPayload):

    try:    
        locks_at = payload.locks_at.replace(tzinfo=None) if payload.locks_at else None
        resolution_date = payload.resolution_date.replace(tzinfo=None) if payload.resolution_date else None
        reserve = payload.b * _math.log(2)

        new_group_market = PredictionMarketGroup(
            question=payload.group_market_question,
            description=payload.group_market_description,
            locks_at=locks_at,
            resolution_date=resolution_date,
            resolution_source=payload.resolution_source,
        )

        db.add(new_group_market)
        await db.commit()
        await db.refresh(new_group_market)

        # we then use a for loop to create the individual binary mkts for the group mkt
        for bn_option in payload.submarket_entries: # bn just mean binary market

            new_market = PredictionMarket(
            creator_id=None, # since it is created by the admin
            question= f"{payload.group_market_question} : => {bn_option}",
            description=payload.group_market_description,
            category=payload.category,
            resolution_source=payload.resolution_source,
            locks_at=locks_at,
            resolution_date=resolution_date,
            market_status=(
                PredictionMarketStatus.active
                if payload.go_live_immediately
                else PredictionMarketStatus.pending_approval
            ),
            b=payload.b, # this is the value that we set that controls the liquidity of the market
            q_yes=0.0,
            q_no=0.0,
            total_collected=0.0,
            house_reserve=reserve, # this amount must be present and the house does not mind losing this money at any point
            market_group_id=new_group_market.id, 
            )
            
            db.add(new_market)
            await db.commit()
            await db.refresh(new_market)

        
        # the final return maessage after creation of group mkt and sub mkts
        return {"message": "Group market created successfully", "group_market_id": new_group_market.id}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"admin create group market failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"admin create gropu market failed: {str(e)}"
        )

@admin_router.post("/create_fixture_prediction_market")
async def admin_create_fixture_prediction_market(
    db: db_dependancy,
    payload: AdminCreateFixturePredictionMarket
):
    try:
        locks_at = payload.locks_at.replace(tzinfo=None) if payload.locks_at else None
        resolution_date = payload.resolution_date.replace(tzinfo=None) if payload.resolution_date else None
        reserve = payload.b * _math.log(3) # three way 
        
        match_data = await db.execute(select(Fixture).where(Fixture.local_id == payload.fixture_id))
        match = match_data.scalar_one_or_none()
        if not match:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= "Fixture not found"
            )

        new_match_prediction_market = FixtureBasedMarket(
        fixture_id=payload.fixture_id,
        question=f"{match.home_team} vs {match.away_team}",
        description=f"Predict the outcome of {match.home_team} vs {match.away_team}",
        category=payload.category,
        b=payload.b,
        locks_at=locks_at,
        resolution_date=resolution_date,
        resolution_source=payload.resolution_source,
        house_reserve=reserve,
        market_status=(
            PredictionMarketStatus.active
            if payload.go_live_immediately
            else PredictionMarketStatus.pending_approval
            ),
        )

        db.add(new_match_prediction_market)
        await db.commit()
        await db.refresh(new_match_prediction_market)

        return {"message": "Fixture market created successfully", "Fixture market id": new_match_prediction_market.id}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"admin create fixture prediction market failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"admin create fixture prediction market failed: {str(e)}"
        )