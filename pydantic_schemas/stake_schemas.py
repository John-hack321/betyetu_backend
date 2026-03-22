from typing import Optional
from pydantic import BaseModel
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class StakeWinner(str, Enum):
    owner = "owner"
    guest = "guest"
    none = "none"

class StakeStatus(str, Enum):
    successfull = "successfull"   # stake fully completed, funds sent
    pending = "pending"           # waiting for a guest to join
    progressing = "progressing"   # joined, match not played yet


# ── DB row representation (mirrors the ORM columns) ──────────────────────────

class StakeBaseModel(BaseModel):
    """
    Direct representation of a Stake ORM row.
    Used internally when reading rows back from the DB — NOT sent to the frontend.
    All fields are optional to handle partial reads gracefully.
    """
    id: Optional[int] = None
    user_id: Optional[int] = None
    match_id: Optional[int] = None
    home: Optional[str] = None
    away: Optional[str] = None
    placement: Optional[str] = None
    amount: Optional[int] = None
    invited_user_id: Optional[int] = None
    invited_user_placement: Optional[str] = None
    invited_user_amount: Optional[int] = None
    invite_code: Optional[str] = None
    stake_status: Optional[StakeStatus] = None
    winner: Optional[StakeWinner | str] = None
    possibleWin: Optional[int] = None
    public: bool = False

    class Config:
        from_attributes = True


# ── Frontend response objects ─────────────────────────────────────────────────

class UserStakeObject(BaseModel):
    """Returned to regular users from /stakes/get_user_stakes"""
    stakeId: int
    home: str
    away: str
    stakeAmount: Optional[int] = None
    stakeStatus: str                   # "pending" | "successful" | "progressing"
    stakeResult: str                   # "pending" | "won" | "lost"
    date: str                          # ISO string from created_at
    possibleWin: Optional[int | str] = None
    inviteCode: Optional[str] = None
    placement: Optional[str] = None
    public: Optional[bool] = False


class AdminStakeObject(BaseModel):
    """Returned to admin from /admin/stakes/all_user_stakes"""
    stakeId: int
    role: str                          # "owner" | "guest"
    userId: int
    invited_user_id: Optional[int] = None
    amount: Optional[int] = None
    invited_user_amount: Optional[int] = None
    match_id: Optional[int] = None
    home: str
    away: str
    stakeType: Optional[bool] = None   # public flag
    winner: str                        # "pending" | "won" | "lost"
    inviteCode: Optional[str] = None
    possibleWin: Optional[int] = None
    stakeStatus: str
    placement: Optional[str] = None


# ── Payload models (request bodies) ──────────────────────────────────────────

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


# ── Stake detail view (while actively staking / previewing) ──────────────────

class StakeOwner(BaseModel):
    stakeAmount: int
    stakePlacement: str

class StakeGeust(BaseModel):
    stakeAmount: Optional[int] = 0
    stakePlacement: Optional[str] = ""

class StakeDataObject(BaseModel):
    stakeId: int
    matchId: int
    homeTeam: str
    awayTeam: str
    stakeOwner: StakeOwner
    stakeGeust: StakeGeust


# ── Collection wrappers ───────────────────────────────────────────────────────

class UserStakesReturnObject(BaseModel):
    status: str
    message: str
    stakeData: list[UserStakeObject]

class AdminStakesReturnObject(BaseModel):
    status: str
    message: str
    stakeData: list[AdminStakeObject]


# ── Legacy aliases (kept so existing imports don't break immediately) ─────────
# These point to the user-facing model which is the original intent of StakeObject.
StakeObject = UserStakeObject
StakesReturnObject = UserStakesReturnObject


# ── Misc ──────────────────────────────────────────────────────────────────────

class StakeInitiationPayload(BaseModel):
    match_id: int
    placement: str
    amount: int
    home: str
    away: str