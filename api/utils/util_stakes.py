from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.exc import AsyncContextAlreadyStarted
from sqlalchemy.future import select

from pydantic_schemas.stake_schemas import GuestStakeJoiningPayload, OwnerStakeInitiationPayload, StakeBaseModel
from db.models.model_stakes import Stake
from pydantic_schemas.stake_schemas import stake_status

"""
I set the stake initiation payload type to the stake base model because with pydantic this it can handle
both occasions for creating and joining a stake object 
"""
async def create_stake_object(db: AsyncSession, stake_data: StakeBaseModel, user_id: int, invite_code: str):
    db_object= Stake(
        user_id= user_id,
        match_id= stake_data.match_id,
        placement= stake_data.placement,
        amount= stake_data.amount,
        invite_code= invite_code,
        stake_status= stake_status.pending,
    )
    db.add(db_object)
    await db.commit()
    await db.refresh(db_object)
    return db_object

async def get_stake_by_invite_code_from_db(db: AsyncSession, invite_code: str):
    query= select(Stake).where(Stake.invite_code == invite_code)
    result= await db.execute(query)
    return result.scalars().first()

"""
add the guest stake data to the stakes table
"""
async def add_guest_stake_data_to_db(db: AsyncSession, user_id: int, guest_stake_data: GuestStakeJoiningPayload):
    query= select(Stake).where(Stake.id == guest_stake_data.stakeId)
    result= await db.execute(query)
    db_object= result.scalars().first()
    db_object.invited_user_amount= guest_stake_data.stakeAmount
    db_object.placement= guest_stake_data.placement
    db_object.invited_user_id= user_id
    await db.commit()
    await db.refresh(db_object)
    return db_object

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