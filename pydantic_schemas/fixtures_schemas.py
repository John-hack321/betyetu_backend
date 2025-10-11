from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# this is a represenstation of the parsed match object from the api call
class MatchObject(BaseModel):
    match_id : int
    home_team_id : int
    home_team : str
    away_team_id : int
    away_team : str
    match_date: datetime
    is_played: bool
    outcome : Optional[str] = None
    home_score : int
    away_score : int
    is_played: bool
    league_id : int