from pydantic import BaseModel
from typing import Optional

from db.models.model_fixtures import FixtureStatus

class HomeLiveMatch(BaseModel):
    id: int
    score: int
    name: str
    longName: str
    redCards: Optional[int] = None  # Added since some matches have red cards

class AwayLiveMatch(BaseModel):
    id: int
    score: int
    name: str
    longName: str
    redCards: Optional[int] = None  # Added since some matches have red cards

class HalfsModel(BaseModel):
    firstHalfStarted: str
    secondHalfStarted: Optional[str] = None  # Not all matches have second half started

class LiveTimeModel(BaseModel):
    short: str
    shortKey: str
    long: str
    longKey: str
    maxTime: int
    addedTime: int

class LiveMatchStatus(BaseModel):
    utcTime: str
    halfs: HalfsModel
    periodLength: int
    finished: bool
    started: bool
    cancelled: bool
    ongoing: bool
    scoreStr: str
    liveTime: LiveTimeModel
    numberOfHomeRedCards: Optional[int] = None  # Added for matches with red cards
    numberOfAwayRedCards: Optional[int] = None  # Added for matches with red cards
    # Note: timeTs is at the LiveMatch level, not here

class LiveMatch(BaseModel):
    id: int
    leagueId: int
    time: str
    home: HomeLiveMatch
    away: AwayLiveMatch
    eliminatedTeamId: Optional[int] = None
    statusId: int
    tournamentStage: str
    status: LiveMatchStatus
    timeTS: int  # This is the timestamp field

class LiveResponseWrapper(BaseModel):
    """Wrapper for the live matches array"""
    live: list[LiveMatch]

class LiveFootballDataResponse(BaseModel):
    status: str
    response: LiveResponseWrapper  # Changed from list[LiveMatch] to LiveResponseWrapper

class RedisStoreLiveMatch(BaseModel):
    matchId: str
    leagueId: str
    homeTeam: str
    awayTeam: str
    homeTeamScore: int
    awayTeamScore: int
    time: str

class RedisStoreLiveMatchVTwo(BaseModel):
    matchId: str
    leagueId: str
    homeTeam: str
    awayTeam: str
    homeTeamScore: int
    awayTeamScore: int
    date: str
    time: str
    fixtureStatusInDb: FixtureStatus

# just defined the full modle just incase i add something that might need the other part , but for later on we will optimize more
class HalfsDetails(BaseModel):
    firstHalfStarted: str = ""
    firstHalfEnded: str = ""
    secondHalfStarted: str = ""
    secondHalfEnded: str = ""
    firstExtraHalfStarted: str = ""
    secondExtraHalfStarted: str = ""
    gameEnded: str = ""

class ReasonDetails(BaseModel):
    short: str = ""
    shortKey: str = ""
    long: str = ""
    longKey: str = ""

class MatchScoreDetails(BaseModel): # so this is the root of the response
    status: str
    response: 'MatchScoreResponse'

class MatchScoreResponse(BaseModel):
    status: 'MatchStatus'

class MatchStatus(BaseModel):
    utcTime: str = ""
    numberOfHomeRedCards: int = 0
    numberOfAwayRedCards: int = 0
    halfs: Optional[HalfsDetails] = None
    finished: bool = False
    started: bool = False
    cancelled: bool = False
    awarded: bool = False
    scoreStr: str = ""
    reason: Optional[ReasonDetails] = None
    whoLostOnPenalties: Optional[str] = None
    whoLostOnAggregated: str = ""

class ParsedScoreData(BaseModel):
    homeScore: int
    awayScore: int
    finished: bool