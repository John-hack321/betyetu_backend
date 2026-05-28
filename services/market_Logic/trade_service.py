import logging
import sys

from fastapi import HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.model_prediction_market import (
    PredictionMarket,
    PredictionMarketOutcome,
    PredictionMarketPosition,
    PredictionMarketStatus,
    PredictionMarketTrade,
    PredictionPositionStatus,
    PredictionTradeType
    )

from db.models.model_users import Account
from services.market_Logic.LMSR import (
    cost_to_buy,
    payout_from_sell,
    yes_price,
    no_price,
    cost_function,
    max_house_loss,
    shares_for_budget,
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

# Buy shares 
async def process_buy(
    db: AsyncSession,
    market_id: int,
    user_id: int,
    side: str,
    shares: float | None = None,   # None when called via budget_kes path
    budget_kes: float | None = None,
    platform_fee_pct: float = 0.02,
) -> dict:
    """
    Atomically buys shares. Accepts either:
    - shares: a fixed share count (existing /buy endpoint)
    - budget_kes: a KES amount to convert to shares inside the transaction
        (the /buy_shares_of_x_amount endpoint — avoids touching db before begin())
    """
    async with db.begin():

        # Step 1: Lock the market row
        market = await db.scalar(
            select(PredictionMarket)
            .where(PredictionMarket.id == market_id)
            .with_for_update()
        )

        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status != PredictionMarketStatus.active:
            raise HTTPException(
                status_code=423,
                detail=f"Market is {market.market_status.value}, trading is closed"
            )

        # Step 1b: Convert budget → shares if called via buy_shares_of_x_amount
        if shares is None:
            if budget_kes is None or budget_kes <= 0:
                raise HTTPException(status_code=400, detail="Amount must be positive")
            PLATFORM_FEE = 0.02
            base_budget = budget_kes / (1 + PLATFORM_FEE)
            shares = shares_for_budget(
                q_yes=market.q_yes,
                q_no=market.q_no,
                b=market.b,
                budget=base_budget,
                side=side,
            )
            if shares <= 0:
                raise HTTPException(status_code=400, detail="Amount too small to purchase any shares")

        # Steps 2–7 remain exactly as before (no changes needed)
        base_cost = cost_to_buy(market.q_yes, market.q_no, market.b, shares, side)
        fee        = base_cost * platform_fee_pct
        total_cost = base_cost + fee

        result = await db.execute(
            update(Account)
            .where(
                Account.user_id == user_id,
                Account.balance >= int(total_cost)
            )
            .values(balance=Account.balance - int(total_cost))
            .returning(Account.balance)
        )
        new_balance_row = result.fetchone()

        if new_balance_row is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient balance. This trade costs {total_cost:.2f} KES."
            )

        new_balance = new_balance_row[0]

        if side == "yes":
            market.q_yes += shares
        else:
            market.q_no += shares

        market.total_collected += base_cost

        p_yes_after = yes_price(market.q_yes, market.q_no, market.b)
        p_no_after  = 1.0 - p_yes_after

        side_enum = PredictionMarketOutcome.yes if side == "yes" else PredictionMarketOutcome.no

        existing_position = await db.scalar(
            select(PredictionMarketPosition)
            .where(
                PredictionMarketPosition.market_id == market_id,
                PredictionMarketPosition.user_id   == user_id,
                PredictionMarketPosition.side      == side_enum,
            )
            .with_for_update()
        )

        if existing_position:
            existing_position.shares_held  += shares
            existing_position.total_cost   += base_cost
            existing_position.average_cost_per_share = (
                existing_position.total_cost / existing_position.shares_held
            )
        else:
            new_position = PredictionMarketPosition(
                market_id=market_id,
                user_id=user_id,
                side=side_enum,
                shares_held=shares,
                total_cost=base_cost,
                average_cost_per_share=base_cost / shares,
                position_status=PredictionPositionStatus.open,
            )
            db.add(new_position)

        trade = PredictionMarketTrade(
            market_id=market_id,
            user_id=user_id,
            trade_type=PredictionTradeType.buy,
            side=side_enum,
            shares=shares,
            kes_amount=total_cost,
            yes_price_at_trade=p_yes_after,
            q_yes_after=market.q_yes,
            q_no_after=market.q_no,
        )
        db.add(trade)

    return {
        "trade_id": trade.id,
        "market_id": market_id,
        "side": side,
        "trade_type": "buy",
        "shares": shares,
        "kes_amount": total_cost,
        "yes_price_after": round(p_yes_after, 6),
        "no_price_after": round(p_no_after, 6),
        "new_account_balance": new_balance,
    }

# Sell shares 

async def process_sell(
    db: AsyncSession,
    market_id: int,
    user_id: int,
    side: str,
    shares: float,
    platform_fee_pct: float = 0.02,
) -> dict:
    """
    Atomically:
    1. Lock the market row.
    2. Lock and check the user's position (they must own enough shares).
    3. Calculate payout using LMSR.
    4. Deduct fee from payout.
    5. Credit net payout to user's account.
    6. Update q values and position.
    7. Write trade record.
    8. Commit.
    """
    async with db.begin():

        # 1: Lock market 
        market = await db.scalar(
            select(PredictionMarket)
            .where(PredictionMarket.id == market_id)
            .with_for_update()
        )

        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status != PredictionMarketStatus.active:
            raise HTTPException(
                status_code=423,
                detail=f"Market is {market.market_status.value}, cannot sell"
            )

        # Step 2: Lock and check position 
        side_enum = PredictionMarketOutcome.yes if side == "yes" else PredictionMarketOutcome.no

        position = await db.scalar(
            select(PredictionMarketPosition)
            .where(
                PredictionMarketPosition.market_id == market_id,
                PredictionMarketPosition.user_id   == user_id,
                PredictionMarketPosition.side      == side_enum,
                PredictionMarketPosition.position_status == PredictionPositionStatus.open,
            )
            .with_for_update()
        )

        if not position:
            raise HTTPException(
                status_code=404,
                detail=f"You don't have an open {side.upper()} position in this market"
            )

        if shares > position.shares_held:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"You only have {position.shares_held:.4f} {side.upper()} shares. "
                    f"Cannot sell {shares:.4f}."
                )
            )

        #  Step 3: Calculate payout 
        gross_payout = payout_from_sell(market.q_yes, market.q_no, market.b, shares, side)
        fee          = gross_payout * platform_fee_pct
        net_payout   = gross_payout - fee # we need to look into this market fee issue in the trade sevice and make sure it is no kaliaring our usrs

        # Step 4: Credit user account 
        result = await db.execute(
            update(Account)
            .where(Account.user_id == user_id)
            .values(balance=Account.balance + int(net_payout))
            .returning(Account.balance)
        )
        new_balance = result.fetchone()[0]

        # Step 5: Update market state 
        if side == "yes":
            market.q_yes -= shares
        else:
            market.q_no -= shares

        market.total_collected -= gross_payout  # net redemption reduces the pool


        p_yes_after = yes_price(market.q_yes, market.q_no, market.b)
        p_no_after  = 1.0 - p_yes_after

        # Step 6: Update position 
        # unlike in buy processing here we dont need to query position first since we know it is existent
        position.shares_held -= shares
        position.total_cost  -= (position.average_cost_per_share * shares)

        if position.shares_held <= 0.0001:  # treat near-zero as fully closed
            position.shares_held = 0.0
            position.total_cost  = 0.0
            position.position_status = PredictionPositionStatus.closed

        # Step 7: Write trade record 
        trade = PredictionMarketTrade(
            market_id=market_id,
            user_id=user_id,
            trade_type=PredictionTradeType.sell,
            side=side_enum,
            shares=shares,
            kes_amount=net_payout,
            yes_price_at_trade=p_yes_after,
            q_yes_after=market.q_yes,
            q_no_after=market.q_no,
        )
        db.add(trade)

    return {
        "trade_id": trade.id,
        "market_id": market_id,
        "side": side,
        "trade_type": "sell",
        "shares": shares,
        "kes_amount": net_payout,
        "yes_price_after": round(p_yes_after, 6),
        "no_price_after": round(p_no_after, 6),
        "new_account_balance": new_balance,
    }


# Admin: resolve market
# this is done by the admin only : that is me
async def process_market_resolution(
    db: AsyncSession,
    market_id: int,
    outcome: str,           # "yes" or "no"
    outcome_notes: str = None,
) -> dict:
    """
    Admin resolves the market.  All winning positions get paid out 1 KES/share.
    Losing positions get 0.

    This is the ONLY function that should ever set market_status = resolved.
    Call it from the admin dashboard endpoint.

    Steps:
    1. Lock market, verify it's in locked status.
    2. Fetch all open positions for the winning side.
    3. For each position: credit 1 KES * shares_held to user, mark settled.
    4. Mark market as resolved.
    5. Commit everything.
    """
    async with db.begin():

        # Step 1: Lock market 
        market = await db.scalar(
            select(PredictionMarket)
            .where(PredictionMarket.id == market_id)
            .with_for_update()
        )

        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status not in (
            PredictionMarketStatus.locked,
            PredictionMarketStatus.active,
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Market must be active or locked to resolve. Current: {market.market_status.value}"
            )

        outcome_enum = PredictionMarketOutcome.yes if outcome == "yes" else PredictionMarketOutcome.no
        losing_side  = PredictionMarketOutcome.no  if outcome == "yes" else PredictionMarketOutcome.yes

        # Step 2: Fetch all winning positions 
        winning_positions_result = await db.execute(
            select(PredictionMarketPosition)
            .where(
                PredictionMarketPosition.market_id == market_id,
                PredictionMarketPosition.side == outcome_enum,
                PredictionMarketPosition.position_status == PredictionPositionStatus.open,
            )
            .with_for_update()
        )
        winning_positions = winning_positions_result.scalars().all()

        # Step 3: Pay out winning positions 
        total_paid_out = 0.0

        for pos in winning_positions:
            payout = pos.shares_held  # 1 KES per share
            total_paid_out += payout

            # Credit user account
            await db.execute(
                update(Account)
                .where(Account.user_id == pos.user_id)
                .values(balance=Account.balance + int(payout))
            )

            # Mark position as settled
            pos.position_status  = PredictionPositionStatus.settled
            pos.settled_payout   = payout

        # Mark losing positions as settled (they get 0)
        losing_positions_result = await db.execute(
            select(PredictionMarketPosition)
            .where(
                PredictionMarketPosition.market_id == market_id,
                PredictionMarketPosition.side == losing_side,
                PredictionMarketPosition.position_status == PredictionPositionStatus.open,
            )
        )
        for pos in losing_positions_result.scalars().all():
            pos.position_status = PredictionPositionStatus.settled
            pos.settled_payout  = 0.0

        # Step 4: Mark market as resolved 
        market.market_status = PredictionMarketStatus.resolved
        market.outcome       = outcome_enum
        market.outcome_notes = outcome_notes

    return {
        "market_id": market_id,
        "outcome": outcome,
        "positions_paid": len(winning_positions),
        "total_paid_out_kes": total_paid_out,
    }