from pydantic import BaseModel

class LeagueBaseModel(BaseModel):
    id : int
    name : str
    localized_name : str
    logo_url : str