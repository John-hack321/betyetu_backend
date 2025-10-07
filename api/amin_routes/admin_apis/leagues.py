import fastapi
from fastapi import APIRouter

router = APIRouter(
    prefix='/leagues',
    tags=['leagues']
)

@router.get('/leagues')
async def get_leagues_list():
    """
    check if the leagues are in the database
    if not query the api for the leagues
    """
    
    ...