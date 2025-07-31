import fastapi
from fastapi import APIRouter, HTTPException , status
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.dependancies import db_dependancy , user_depencancy
from pydantic_schemas.chess_player_schemas import CreateChessDbProfile, account_status_code
from api.utils.util_chess_players import add_new_chess_player, get_user_by_chess_foreign_username
from api.utils.util_users import get_user_by_id
from services.chess_services.chess_playsers import ChessPlayerService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix = '/chess_foreign',
    tags = ['chess_foreign']
)

@router.get('/add_foreign_data' , status_code=status.HTTP_200_OK)
async def get_chess_foreign_profile_data(username : str , user :  user_depencancy , db : db_dependancy):
    try :
         user_id = user.get('user_id')
         # we will now fetch data from the ednpoint
         try :
            chess_service_instance = ChessPlayerService(username)
            chess_foreing_profile_data = await chess_service_instance.fetch_user_profile_data()
            if not chess_foreing_profile_data :
                raise RuntimeError(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = f"failed to fetch proper profile data : {chess_foreing_profile_data}")
            # after that i belive we then need to add this data to the database 
            new_db_chess_profile_foreign = await add_new_chess_player(db ,chess_foreing_profile_data ,user_id)
            if not new_db_chess_profile_foreign:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = f"failed to create a new db object : {new_db_chess_profile_foreign}")
         except Exception as e :
            logger.error(f'falied to instanciate the chess service : {str(e)}')
            raise RuntimeError(f'failed to instanciate and fetch foreing user data from chess.com')
    except Exception as e :
        logger.error(f'the get chess_foreign_data_endpoint_failed with error : {str(e)}')
        raise RuntimeError(f'the get chess foreign data function failed')

# the endpoint above is used to fetch user data from withing the fronted and i belive it would be better if it first checked if the user existed first before doiing the fetching ?
# for now i will create a seperate endpoint for fetching the foreign chess data that is already in the database then later on i will refacter this into a single merged ednpoint as required

@router.get('/get_chess_data')
async def get_user_chess_data(user : user_depencancy, db : db_dependancy , username : str = None):
    user_id = user.get('user_id')
    db_user = await get_user_by_id(db , user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'failed to fetch db user from database')
    username = db_user.username
    if not username:
        raise RuntimeError(f'username does not exist on the database{username}')
    db_foreign_chess_profile = await get_user_by_chess_foreign_username(db , username)
    if not db_foreign_chess_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'failed to create a db object for the profile data')
    return {
        'player_id' : db_foreign_chess_profile.player_id,
        'username' : db_foreign_chess_profile.username,
        'followers' : db_foreign_chess_profile.followers,
        'country' : db_foreign_chess_profile.country,
        'account_status' : db_foreign_chess_profile.account_status,
        'acount_verification_status' : db_foreign_chess_profile.account_verification_status ,
        'league' : db_foreign_chess_profile.league
    }

@router.get('/add_foreign_chess_data')
async def add_foreign_chess_data(db: db_dependancy, user: user_depencancy, username: str):
    user_id = user.get('user_id')
    try:
        chess_player_instance = ChessPlayerService(username)
        chess_foreign_profile_data = await chess_player_instance.fetch_user_profile_data()
        
        if not chess_foreign_profile_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"The data object from the chess service was invalid: {chess_foreign_profile_data}"
            )
        
        # The chess service now returns a dictionary, so we can pass it directly
        new_db_chess_profile_foreign = await add_new_chess_player(db, chess_foreign_profile_data, user_id)
        
        if not new_db_chess_profile_foreign:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail='Failed to add the profile data to the database'
            )
            
        return {
            'message': 'Chess profile added successfully',
            'player_id': new_db_chess_profile_foreign.player_id,
            'username': new_db_chess_profile_foreign.chess_username
        }
        
    except Exception as e:
        logger.error(f'There was an error running the chessplayer service: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='The chess profile service failed'
        )