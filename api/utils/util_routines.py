from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from pydantic_schemas.routine_schemas import RoutineBase , CreateRoutine
from db.models.model_users import Routine

async def get_routines( db : AsyncSession , user : dict ):
    query = select(Routine).options(joinedload(Routine.workouts)).where(Routine.user_id == user.get('id'))
    result = await db.execute(query)
    return result.scalars().all()

async def create_routine(db : AsyncSession , user : dict , routine : CreateRoutine):
    db_routine = Routine(**routine.model_dump() , user_id = user.get('user_id'))
    for workout_id in routine.workouts:
        workout = db.query(Workout).filter(Workout.workout_id == workout_id).first()
        if workout:
            db_routine.workouts.append(workout)
    db.add(db_routine)
    await db.commit()
    await db.refresh(db_routine)
    db_routines = get_routines( db , user , routine )
    return db_routines