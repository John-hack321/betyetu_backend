from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.orm import query
from db.db_setup import AsyncSession
from db.models.model_stakes import Stake
from pydantic_schemas.stake_schemas import StakeWinner

import logging

logger= logging.getLogger(__name__)

async def get_stakes_from_db(db: AsyncSession):
    query= select(Stake)
    result= await db.execute(query)
    db_stakes_object= result.scalars().all()
    return db_stakes_object


async def set_stake_winner(db: AsyncSession, stake_id: int, side: int):
    try:
        query= select(Stake).where(Stake.id== stake_id)
        result= await db.execute(query)
        db_stake_object= result.scalars().first()

        # magic happens here now
        if side == 1:
            db_stake_object.winner= StakeWinner.owner
        elif side == 2:
            db_stake_object.winner= StakeWinner.guest

        await db.commit()
        await db.refresh(db_stake_object)
        return db_stake_object

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while stting stake winner into the db: {str(e)} ", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while adding winner to the database: {str(e)}"
        )