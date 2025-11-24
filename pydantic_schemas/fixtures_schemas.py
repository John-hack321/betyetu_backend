from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from db.models.model_fixtures import FixtureStatus

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
    fixture_status: FixtureStatus


# data modeling for the score data returned from the match_scores api call
class TeamScore(BaseModel):
    """Represents a team's score in a match."""
    name: str
    id: int = Field(..., gt=0, description="Unique team identifier")
    score: int = Field(..., ge=0, description="Team's score in the match")
    image_url: str = Field(..., alias="imageUrl", description="URL to team logo")
    
    class Config:
        # Allow population by field name or alias
        populate_by_name = True


class ScoresData(BaseModel):
    """Container for match scores."""
    scores: List[TeamScore] = Field(..., min_length=2, max_length=2)


class FixtureScoreResponse(BaseModel):
    """Root response model for fixture score API."""
    status: str
    response: ScoresData
    
    class Config:
        # Example for documentation
        json_schema_extra = {
            "example": {
                "status": "success",
                "response": {
                    "scores": [
                        {
                            "name": "Feyenoord",
                            "id": 10235,
                            "score": 1,
                            "imageUrl": "https://images.fotmob.com/image_resources/logo/teamlogo/10235_small.png"
                        },
                        {
                            "name": "Mancity",
                            "id": 67839,
                            "score": 9,
                            "imageUrl": "https://images.fotmob.com/image_resources/logo/teamlogo/10235_small.png"
                        }
                    ]
                }
            }
        }