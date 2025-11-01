from pydantic import BaseModel
from sqlalchemy.orm import strategy_options

class HomeLiveMatch(BaseModel):
    id: int
    score: int
    name: str
    longName: str

class AwayLiveMatch(BaseModel):
    id: int
    score: int
    name: str
    longName: str

class HalfsModel(BaseModel):
    firstHalfStarted: str
    secondHalfStarted: str

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
    timeTs: str

class LiveMatch(BaseModel):
    id: int
    leagueId: int
    time: str
    home: HomeLiveMatch
    away: AwayLiveMatch
    eliminatedTeamId: int
    statusId: int
    tournamentStage: str
    status: LiveMatchStatus

class LiveFootballDataResponse(BaseModel):
    status: str
    response: list[LiveMatch]