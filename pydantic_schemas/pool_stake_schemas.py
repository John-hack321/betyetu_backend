import datetime
from optparse import Option
from types import NoneType
from typing import Optional
from pydantic import BaseModel

from db.models.model_stakes import PoolStakeChoice, PoolStakeStatus


class PoolStakeBaseModel(BaseModel):
    """
    this is a representation of the PoolStakeModel
    all entries are made to be optional to handle partial read and writes gracfully
    """

    id= Optional[int]= None
    match_id= Optional[int]= None
    league_id= Optional[int] = None
    stake_status= Optional[PoolStakeStatus] = PoolStakeStatus.active
    locks_at= Optional[datetime]= None
    resolution_date= Optional[datetime]= None
    outcome= Optional[PoolStakeChoice]= None
    pool_amount= Optional[int]= 0
    home_pool= Optional[int]= 0
    away_pool= Optional[int]= 0
    draw_pool= Optional[int]= 0
    home_pool_count= Optional[int]= 0
    away_pool_count= Optional[int]= 0
    draw_pool_count= Optional[int]= 0


class PoolEntryBaseModel(BaseModel):
    """
    just like on the poolstake here too the entries are made to be optional to handle partial read and writes gracfully
    """
    id= Optional[int]= None
    pool_stake_id= Option[int]= None
    user_id= Optional[int]= None
    placement= Optional[PoolStakeChoice]= None
    amount= Optional[int]= None
    payout_amount= Optional[int]= None
    possible_win= Optional[int]= None