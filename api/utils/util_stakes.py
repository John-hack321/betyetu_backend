from fastapi import HTTPException
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.exc import AsyncContextAlreadyStarted
from sqlalchemy.future import select
from fastapi import status, HTTPException

from pydantic_schemas.stake_schemas import GuestStakeJoiningPayload, OwnerStakeInitiationPayload, StakeBaseModel, StakeWinner
from db.models.model_stakes import Stake
from db.models.model_users import Account
from pydantic_schemas.stake_schemas import StakeStatus

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

logger= logging.getLogger(__name__)

"""
I set the stake initiation payload type to the stake base model because with pydantic this it can handle
both occasions for creating and joining a stake object 
"""
async def create_stake_object(db: AsyncSession, stake_data: OwnerStakeInitiationPayload, user_id: int, invite_code: str):
    try:
        print(f"the create stake object util function has been reached")
        db_object= Stake(
            user_id= user_id,
            match_id= stake_data.matchId,
            home= stake_data.home,
            away= stake_data.away,
            placement= stake_data.placement,
            amount= stake_data.stakeAmount,
            invite_code= invite_code,
            stake_status= StakeStatus.pending,
        )
        db.add(db_object)
        await db.commit()
        await db.refresh(db_object)
        print(f"stake object for user id {user_id} as been created")
        return db_object
    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured whle creating a stake object: {str(e)}",
        exc_info=True,
        extra={
            "affected_user": user_id
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an erro occured while creating stake object"
        )

async def get_stake_by_invite_code_from_db(db: AsyncSession, invite_code: str):
    try:
        query= select(Stake).where(Stake.invite_code == invite_code)
        result= await db.execute(query)
        return result.scalars().first()

    except Exception as e:
        await db.rollback()
        logger.error(f"an error occured while gettnig stake by invite code from db: {str(e)}",
        exc_info=True,
        extra={
            "invite_code": invite_code
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while fetching stake by invite_code from the db {str(e)}"
        )

"""
add the guest stake data to the stakes table
"""
async def add_guest_stake_data_to_db(db: AsyncSession, user_id: int, guest_stake_data: GuestStakeJoiningPayload):
    try:
        query= select(Stake).where(Stake.id == guest_stake_data.stakeId)
        result= await db.execute(query)
        db_object= result.scalars().first()
        db_object.invited_user_amount= guest_stake_data.stakeAmount
        db_object.invited_user_placement= guest_stake_data.placement
        db_object.invited_user_id= user_id

        # in this process we also need to set the value of the stake to successful too
        db_object.stake_status= StakeStatus.successfull
        
        await db.commit()
        await db.refresh(db_object)
        return db_object

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while adding the guest stake data to the database: {str(e)}",
        exc_info=True,
        extra= {"affected user": user_id})

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while adding guest stake data to the database, {str(e)}"
        )

"""
returns a list of stake objects that were created by the user
"""
async def get_user_stakes_where_user_is_owner_from_db(db: AsyncSession, user_id: int):
    query= select(Stake).where(Stake.user_id== user_id)
    result= await db.execute(query)
    return result.scalars().all()

async def get_user_stakes_where_user_is_guest_from_db(db: AsyncSession, user_id: int):
    query= select(Stake).where(Stake.invited_user_id== user_id)
    result= await db.execute(query)
    return result.scalars().all()

async def delete_stake_from_db_by_invite_code(db: AsyncSession, invite_code: str):
    try:
        query= select(Stake).where(Stake.invite_code == invite_code)
        result= await db.execute(query)
        db_stake_objet= result.scalars().first()

        # we then delete from the database
        await db.delete(db_stake_objet)
        await db.commit()

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while trying to delete stake of invite code: {invite_code} from db: {str(e)}",
        exc_info=True,
        extra={
            "invite_code": invite_code
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to delete stake by invite code from db: {str(e)}"
        )

async def get_stake_by_stake_id_from_db(db: AsyncSession, stake_id: int):
    try:
        query= select(Stake).where(Stake.id== stake_id)
        result= await db.execute(query)
        return result.scalars().first()

    except Exception as e:
        logger.error(f"an error occurd while fetching stake data from the database: {str(e)}",
        exc_info=True,
        extra={
            "affected_stake": stake_id
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured whle fetching stake by id from the database"
        )

async def set_possible_win_and_add_to_db(db: AsyncSession, stake_id: int):
    try:
        query= select(Stake).where(Stake.id== stake_id)
        result= await db.execute(query)
        db_stake_object= result.scalars().first()

        # we as the system provider we get a 10% cut from all stake withdrawals from the system
        # so possible win is there for 90 % of the amount
        owner_amount= db_stake_object.amount
        guest_amount= db_stake_object.invited_user_amount

        possible_win= 0.9 * (owner_amount + guest_amount) # find a way to truncate this amount so that we dont have decimals in any way

        db_stake_object.possibleWin= possible_win

        await db.commit()
        await db.refresh(db_stake_object)

        return db_stake_object

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while setting possible win",
         exc_info=True,
         extra={"affected_stake": stake_id})

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while setting possible win to stake of stake id: {stake_id}"
         )

# used to get the stake by match id from the database
async def update_stake_data_with_match_ended_data(db: AsyncSession, match_id: int):
    try:
        query= select(Stake).where(Stake.match_id== match_id)
        result= await db.execute(query)
        db_stake_object= result.scalars().first()
        return db_stake_object

    except Exception as e:
        logger.error(f"an error occured while getting stake by match id from the database: {str(e)}",
        exc_info=True,
        extra={
            "match_id": match_id
        })

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an error occured while trying to get stake by match_id from the database {str(e)}")


async def update_stake_with_winner_data_and_do_payouts(db: AsyncSession, match_id: int, winner_team: str):
    try: 
        # we are going to do alot of buld updates for the data in this place

        # PAYOUTS ARE DONE IN BULD UPDATES TO THE USER ACCOUNTS
        # TODO: maybe later on send the money automaticaly to the users mpesa if it will be possible by that time
        # bulk update account balances for all owner winners

        await db.execute(
            update(Account)
            .where(Account.user_id.in_(
                select(Stake.user_id)
                .where(
                    Stake.match_id== match_id,
                    Stake.placement== winner_team,
                    Stake.stake_status== StakeStatus.successfull)
            ))
            .values(
                balance= Account.balance + (
                    select(Stake.possibleWin)
                    .where(Stake.user_id == Account.user_id, Stake.match_id== match_id)
                    .scalar_subquery()
                )
            )
        )

        # bulk update account balances for all guest winners
        await db.execute(
            update(Account)
            .where(Account.user_id.in_(
                select(Stake.invited_user_id)
                .where(
                    Stake.match_id== match_id,
                    Stake.invited_user_placement== winner_team,
                    Stake.stake_status== StakeStatus.successfull,
                    Stake.invited_user_id.isnot(None))
            )).values(
                balance= Account.balance + (
                    select(Stake.possibleWin).
                    where(Stake.invited_user_id== Account.user_id, Stake.match_id== match_id)
                )
            )
        )

        # STAKE DATA UPDATES NOW

        # bulk update the stakes where the owner is the stake winner
        await db.execute(
            update(Stake)
            .where(Stake.match_id== match_id, Stake.placement== winner_team)
            .values(winner= StakeWinner.owner)
        )

        # bulk update the stakes where the guest is the stake winner
        await db.execute(
            update(Stake)
            .where(Stake.match_id== match_id, Stake.invited_user_placement== winner_team)
            .values(winner= StakeWinner.guest)
        )

        await db.commit()

        # HANDLING OF CASES WHERE NEITHER THE STAKE OWNER NOR THE STAKE GUEST IS THE WINNER

        await db.execute(
            update(Stake)
            .where(
                Stake.match_id== match_id,
                Stake.placement!= winner_team,
                Stake.invited_user_placement!= winner_team,
            )
            .values(winner= StakeWinner.none)
        )

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while updating stake data with winner data, {str(e)}",
        exc_info=True,
        extra={
            "affected_match_id": match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating stake data with winner data"
        )