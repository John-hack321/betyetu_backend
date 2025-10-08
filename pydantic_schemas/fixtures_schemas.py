from pydantic import BaseModel

# this is a represenstation of the parsed match object from the api call
class MatchObject(BaseModel):
    match_id : str
    home_team_id : str
    home_team : str
    away_team_id : str
    match_date : str
    is_played : bool
    outcome : str = None
    home_score : str
    away_score : str
    is_played : bool