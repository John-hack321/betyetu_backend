from typing import Optional
from pydantic import BaseModel

class GeneralPostResponseModel(BaseModel):
    status_code: str
    message: str
    data: Optional[dict]= None