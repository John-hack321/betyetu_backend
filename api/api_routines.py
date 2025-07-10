from fastapi import APIRouter , status , HTTPException

from api.utils.dependancies import db_dependancy , user_depencancy
from pydantic_schemas.routine_schemas import RoutineBase , CreateRoutine
from api.utils.util_routines import get_routines , create_routine

router = APIRouter(
    prefix = '/routines',
    tags = ['routines']
)

@router.get('/')
async def read_routines(db : db_dependancy , user : user_depencancy):
    db_routines = await get_routines(db = db , user = user)
    return db_routines

@router.post('/')
async def add_routine( db : db_dependancy , routine : CreateRoutine , user : user_depencancy):
    db_routine = await create_routine(db , routine = routine , user = user )
    return db_routine