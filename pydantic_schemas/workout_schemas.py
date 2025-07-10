from pydantic import BaseModel
from typing import Optional

class Workout(BaseModel):
    name : str
    description : Optional[str] = None

class CreateWorkout(Workout):
    ...

