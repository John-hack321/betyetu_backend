from pydantic import BaseModel
from typing import Optional , List

class RoutineBase(BaseModel):
    name : str
    description : Optional[str] = None

class CreateRoutine(RoutineBase):
    workouts_list : List[int] = []