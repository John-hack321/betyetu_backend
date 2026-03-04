from numbers import Number
from typing import Optional
from fastapi.openapi.models import BaseModelWithConfig
from pydantic import BaseModel
from sqlalchemy import Boolean, Null
import enum

from db.db_setup import Base

from enum import Enum

# enum schemas
class StakeWinner(str, Enum):
    owner = "owner"
    guest = "guest"
    none = "none"

class StakeStatus(str, Enum):
    successfull = "successfull" # once the stake has been fully completed and funds sent it will be marked as successful
    pending = "pending" # as stake owner waits for a stake guest to join stake will be marked as pending
    progressing= "progressing" # for stakes that have been joined the match hasn't been played yet



class StakeBaseModel(BaseModel):
    id: Optional[int]
    user_id: Optional[int]= None # made it optionla because I added it too late : TODO : fix this issue later on
    match_id: int
    home: str
    away: str
    placement: str
    amount: int
    invited_user_id: Optional[str]= None
    invited_user_placement: Optional[str]= None
    invited_user_amount: Optional[str]= None
    invite_code: Optional[str]
    stake_status: Optional[StakeStatus]
    winner: Optional[StakeWinner] | str= None
    possibleWin: Optional[int]= None
    public: bool= False

class StakeObject(StakeBaseModel): # this one if for the fetching of stakes from the db for showcase on frontend
    stakeId: int
    userId: int
    role: Optional[str]= None # reserved for the admin fetching
    home: str
    away: str
    stakeAmount: int # this is the Amount in the admin side
    stakeStatus: Optional[StakeStatus | str]
    stakeResult: str
    date: Optional[str]
    inviteCode: Optional[str]= None

class StakeInitiationPayload(BaseModel):
    match_id: int
    placement: str
    amount: int
    home: str
    away: str

# this is what the user(stake_owner) will be sending when initiating a stake
class OwnerStakeInitiationPayload(BaseModel):
    placement: str
    stakeAmount: int
    matchId: int
    home: str
    away: str
    public: bool

class GuestStakeJoiningPayload(BaseModel):
    stakeId: int
    stakeAmount: int
    placement: str


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


class StakesReturnObject(BaseModel):
    status: str
    message: str
    stakeData: list[StakeObject]