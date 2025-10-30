from numbers import Number
from re import S
from typing import Optional
from fastapi.openapi.models import BaseModelWithConfig
from pydantic import BaseModel
from sqlalchemy import Null

from db.db_setup import Base

class StakeWinner(enum.IntEnum):
    owner: 1
    guest: 2

class StakeStatus(enum.IntEnum):
    successfull: 1
    pending: 0



class StakeBaseModel(BaseModel):
    id: int
    match_id: int
    home: str
    away: str
    placement: str
    amount: int
    invited_user_id: Optional[str]= None
    invited_user_placement: Optional[str]= None
    invited_user_amount: Optional[str]= None
    invite_code: str
    stake_status: StakeStatus
    winner: Optional[StakeWinner]= None

class StakeInitiationPayload(BaseModel):
    match_id: int
    placement: str
    amount: int
    home: str
    away: str

class OwnerStakeInitiationPayload(BaseModel):
    placement: str
    stakeAmount: int
    matchId: int
    home: str
    away: str

class GuestStakeJoiningPayload(BaseModel):
    stakeId: int
    stakeAmount: str
    placement: int


class StakeOwner(BaseModel):
    stakeAmount: int
    stakePlacement: str

class StakeGeust(BaseModel):
    stakeAmount: Optional[int]= 0
    stakePlacement: Optional[str]= ""


class StakeDataObject(BaseModel): # this one if for the fetching of stake data while actively staking
    stakeId: int
    matchId: int
    stakeId: int
    homeTeam: str
    awayTeam: str
    stakeOwner: StakeOwner
    stakeGeust: StakeGeust

class StakeObject(BaseModel): # this one if for the fetching of stakes from the db for showcase on frontend
    home: str
    away: str
    stakeAmount: int
    stakeStatus: StakeStatus
    stakeResult: str
    date: str

class StakesReturnObject(BaseModel):
    status: str
    message: str
    stakeData: list[StakeObject]