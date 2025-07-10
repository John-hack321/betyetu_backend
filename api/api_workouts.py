from sqlalchemy.sql.functions import user
from fastapi import APIRouter , status , HTTPException
from pydantic_schemas.workout_schemas import Workout , CreateWorkout

from api.utils.dependancies import db_dependancy , user_depencancy
from api.utils.util_workouts import get_workouts , get_workout , create_workout , delete_workout

router = APIRouter(
    prefix = '/workouts',
    tags = ['workouts']
)

# this first endpoint here is for getting a single workout 
@router.get('/' , status_code = status.HTTP_200_OK)
async def read_workout(db : db_dependancy , user : user_depencancy , workout_id : int ):
    db_workout = await get_workout( db = db , user = user , workout_id = workout_id )
    return db_workout

@router.get('/workouts' , status_code = status.HTTP_302_FOUND)
async def read_workouts_list( db : db_dependancy , user : user_depencancy):
    db_workouts = await get_workouts( db = db , user = user )
    return db_workouts # this returns a list of all workouts from the database in relation to a user 

@router.post('/' , status_code = status.HTTP_201_CREATED)
async def add_workout(db : db_dependancy , workout : CreateWorkout , user : user_depencancy):
    new_db_workout = await create_workout( db = db , workout = workout , user = user)
    return new_db_workout

# lets implement now an endpoint for deleting a workout
@router.delete('/')
async def remove_workout(db : db_dependancy , user : user_depencancy , workout_id : int):
    db_workout = await delete_workout(db , user = user , workout_id = workout_id)
    return db_workout
    




























