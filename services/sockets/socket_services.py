from fastapi import HTTPException, status

import socketio
import logging

from services.caching_services.redis_client import get_live_match_data_from_redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

# setting up socket io for the project
sio_server = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins = [], # this is left blanck so that fastapi can handle the cors on its own
)

sio_app = socketio.ASGIApp(
    socketio_server = sio_server,
    socketio_path = 'sockets'
)

# I belive this function should be called at startup to make the room id generated once
# and maybe i should store room id in the database

# since we will only have this one room we make it hard typed and alway accessible to anyone
room_id= "live_matches_room"

# TODO: define a pydantic model for the user_data pyaload for joing a room
async def join_room_for_live_data(user_data):
    try: 
        await sio_server.enter_room(user_data.get("sid"), user_data.get("room_id"))

    except Exception as e:
        logger.error(f"an error occured whiel user {user_data.get('user_id')} of sid {sid} was trying to join live data room: {str(e)}",
        extra={
            "affected_user": user_data.get("user_id"),
            "affected_user_sid": user_data.get("sid"),
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to join a live room for live data, {str(e)}"
        )

# this function will handle sending live data to the other users via socketio 
# this occurs everytim a change is made to the data on redis
@sio_server.event
async def send_live_data_to_users(updated_match_ids_list: list[int]):
    # we first have to fetch this data from redis
    try:
        live_match_updates= []

        for item in updated_match_ids_list:
            live_match= await get_live_match_data_from_redis(item)
            live_match_updates.append(live_match)

        await sio_server.emit('send_live_data_to_users', {"liveMatchData": live_match_updates})

    except HTTPException:
        raise # we raise these again

    except Exception as e:

        logger.error(f"an error occured while seding live data to users: {str(e)}",
        exc_info=True,
        extra={
            "league ids": updated_match_ids_list,
        })

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while sending live match data to users"
        )
    
@sio_server.event
async def connect(sid , environ , auth = None):
    try:
        print(f'the connection has been established for the sid {sid}')
        await sio_server.emit('join' , {'sid' : sid , 'message': 'Connected successfully'}) 

    except Exception as e:
        logger.error(f"an error occured while trying to connect to socketio, {str(e)}",
         exc_info=True,
         extra={
            "affected sid": sid
         })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to conncet to socketion fastapi server: {str(e)}"
        )

# no error handling needed for disconnect event as disconnection is automatic
@sio_server.event
async def disconnect(sid , environ):
    print(f'the sid {sid} as been disconnected')