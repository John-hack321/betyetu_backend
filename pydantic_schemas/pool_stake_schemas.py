import datetime
from optparse import Option
from types import NoneType
from typing import Optional, Union, Literal
from pydantic import BaseModel

from db.models.model_stakes import PoolStakeChoice, PoolStakeStatus


class PoolStakeBaseModel(BaseModel):
    """
    this is a representation of the PoolStakeModel
    all entries are made to be optional to handle partial read and writes gracfully
    """

    id: Optional[int] = None
    match_id: Optional[int] = None
    league_id: Optional[int] = None
    stake_status: Optional[PoolStakeStatus] = None
    locks_at: Optional[datetime.datetime] = None
    resolution_date: Optional[datetime.datetime] = None
    outcome: Optional[PoolStakeChoice] = None
    pool_amount: Optional[int] = None
    home_pool: Optional[int] = None
    away_pool: Optional[int] = None
    draw_pool: Optional[int] = None
    home_pool_count: Optional[int] = None
    away_pool_count: Optional[int] = None
    draw_pool_count: Optional[int] = None

class PoolEntryBaseModel(BaseModel):
    """
    just like on the poolstake here too the entries are made to be optional to handle partial read and writes gracfully
    """
    id: Optional[int] = None
    pool_stake_id: Optional[int] = None
    user_id: Optional[int] = None
    placement: Optional[PoolStakeChoice] = None
    amount: Optional[int] = None
    payout_amount: Optional[int] = None

class poolStakeJoiningPyalod(BaseModel):
    """
    for joing the pool stakes
    """
    userStakeAmount: int
    userStakeChoice: Literal["home", "away", "draw"]
    poolStakeId: int