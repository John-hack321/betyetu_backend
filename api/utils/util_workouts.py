from tkinter import W
from sqlalchemy.orm import Session 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models.model_users import Workout
from pydantic_schemas.workout_schemas import CreateWorkout

async def get_workout( db : AsyncSession , user : dict , workout_id : int ):
    query = select(Workout).where(Workout.id == workout_id )
    resutl = await db.execute(query)
    return resutl.scalars().first()

# now lets create another one but now for getting all of the workouts 
async def get_workouts( db : AsyncSession , user : dict):
    query = select(Workout)
    result = await db.execute(query)
    return result.scalars().all()

async def create_workout( db : AsyncSession , workout : CreateWorkout , user : dict):
    db_workout =  Workout(**workout.model_dump() , user_id = user.get('user_id')
)
    db.add(db_workout)
    await db.commit()
    await db.refresh(db_workout)
    return db_workout

async def delete_workout( db : AsyncSession , user : dict , workout_id : int):
    db_workout = await get_workout(db , user = user , workout_id = workout_id)
    if db_workout :
        db.delete(db_workout)
        await db.commit()
        await db.refresh(db_workout)
        return db_workout