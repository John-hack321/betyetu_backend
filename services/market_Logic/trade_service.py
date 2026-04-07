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
    side: str,        # "yes" or "no"
    shares: float,
    platform_fee_pct: float = 0.02,   # in future we will try 2% platform cut on buys => for now we just put it at 0.00 as we try to figure out a better pricing of the sytem in order not to disadvantage the user
) -> dict:
    """
    Atomically: : NOTE: we need to do this atomic thing on ohter parts of the sytem that handle critical code too .
    1. Lock the market row (SELECT FOR UPDATE) — no other trade can read q_yes/q_no until we commit.
    2. Calculate cost using LMSR.
    3. Deduct cost + fee from user's account (atomically, with balance check).
    4. Update q_yes or q_no on the market.
    5. Update (or create) the user's position.
    6. Write a trade record.
    7. Commit everything together.

    If any step fails, the whole thing rolls back.
    """
    async with db.begin():

        # Step 1: Lock the market row 
        market = await db.scalar(
            select(PredictionMarket)
            .where(PredictionMarket.id == market_id)
            .with_for_update() # locks the row and this is very ciritical for us.
        )

        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        if market.market_status != PredictionMarketStatus.active:
            raise HTTPException(
                status_code=423,
                detail=f"Market is {market.market_status.value}, trading is closed"
            )

        # Step 2: Calculate cost 
        # This uses the current locked q_yes and q_no values.
        # No race condition possible because we hold the row lock.
        base_cost = cost_to_buy(market.q_yes, market.q_no, market.b, shares, side)
        fee        = base_cost * platform_fee_pct
        # this toal cost is what we will deduct from the usrs account
        total_cost = base_cost + fee # just as I said we will decide on the pricin later on.

        # Step 3: Deduct from user account atomic with balance check 
        # Using a single SQL UPDATE with a WHERE balance >= total_cost.
        # If balance is insufficient, 0 rows are updated → we detect it.
        result = await db.execute(
            update(Account)
            .where(
                Account.user_id == user_id,
                Account.balance >= int(total_cost)   # balance is stored as int KES
            )
            .values(balance=Account.balance - int(total_cost))
            .returning(Account.balance)
        )
        new_balance_row = result.fetchone() # fetches one row of the result possibly the first row of the results

        if new_balance_row is None:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient balance. This trade costs {total_cost:.2f} KES."
            )

        new_balance = new_balance_row[0] # I belive we should do this to support atomic operatoins and to leave no room for error

        # Step 4: Update market state 
        if side == "yes":
            market.q_yes += shares
        else:
            market.q_no += shares

        market.total_collected += base_cost  # we track base cost, not fee

        # Step 5: Calculate new prices (after the trade) 
        p_yes_after = yes_price(market.q_yes, market.q_no, market.b)
        p_no_after  = 1.0 - p_yes_after

        # Step 6: Update or create position 
        side_enum = PredictionMarketOutcome.yes if side == "yes" else PredictionMarketOutcome.no

        existing_position = await db.scalar( # we first query to check if the user has an existing position , if so we will update the position othewise we will create a new one
            select(PredictionMarketPosition)
            .where(
                PredictionMarketPosition.market_id == market_id,
                PredictionMarketPosition.user_id   == user_id,
                PredictionMarketPosition.side      == side_enum,
            )
            .with_for_update() # we lock this row as we do this update
        )

        if existing_position:
            # Update existing position
            existing_position.shares_held  += shares
            existing_position.total_cost   += base_cost  # track base cost, not incl fee
            existing_position.average_cost_per_share = (
                existing_position.total_cost / existing_position.shares_held
            )
        else:
            # Create new position
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

        # Step 7: Write trade record 
        trade = PredictionMarketTrade(
            market_id=market_id,
            user_id=user_id,
            trade_type=PredictionTradeType.buy,
            side=side_enum,
            shares=shares,
            kes_amount=total_cost,    # what user actually paid (incl fee) : I have mixed feelings about this fee thing but we will look into it
            yes_price_at_trade=p_yes_after,
            q_yes_after=market.q_yes,
            q_no_after=market.q_no,
        )
        db.add(trade)

    # db.begin() auto-commits here on exit if no exception was raised.
    # If any exception was raised above, it auto-rolls back. Nothing partial survives.
    # so the secret to writing atomic code is using using db.begin()

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