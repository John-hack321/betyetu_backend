from fastapi import HTTPException, status

import sys
import socketio
import logging

from pydantic_schemas.live_data import LiveMatch
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
LIVE_MATCHES_ROOM_ID= "live_matches_room"

# AVOID THESE ONES THEY ARE FOR THE PREVIOUS LIVE DATA FUNCTIONALITY
async def update_match_to_live_on_frontend_with_live_data_too(match_id: int):
    try:
        live_match= await get_live_match_data_from_redis(match_id)

        logger.info(f"broadcasting live match {live_match} to users now")

        await sio_server.emit('upate_match_to_live_on_frontend_with_live_data_too',
        {'live_match_data': live_match},
        room= LIVE_MATCHES_ROOM_ID)

    except Exception as e:
        logger.error(f"an error occured while updating match to live on frontend: {str(e)}",
        exc_info=True,
        extra={
            "affected_match_id": match_id
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating match to live on frontend, {str(e)}"
        )

# this function will handle sending live data to the other users via socketio 
# this occurs everytim a change is made to the data on redis
async def send_live_data_to_users(updated_match_ids_list: list[int]):
    # we first have to fetch this data from redis
    try:
        live_match_updates= []

        for item in updated_match_ids_list:
            live_match= await get_live_match_data_from_redis(item)
            live_match_updates.append(live_match)

        await sio_server.emit('send_live_data_to_users',
        {"liveMatchData": live_match_updates},
        room= LIVE_MATCHES_ROOM_ID)

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

# THEY END HERE 


# NEWER FUNCTIONALITY FOR THE NEW LIVE DATA BACKUP STYLE
    
@sio_server.event
async def connect(sid , environ , user_data ,auth = None):
    try:
        print(f'the connection has been established for the sid {sid}')

        await sio_server.enter_room(sid, room=LIVE_MATCHES_ROOM_ID)

        await sio_server.emit('join' , {'sid' : sid , 'message': 'Connected successfully'}) 
        logger.info(f"the user of sid: {sid} has successfuly joined the room")

        await sio_server.emit('connection_confirmed',
        {
            "sid": sid,
            "message": "connection successful",
            "room": LIVE_MATCHES_ROOM_ID
        },
        to=sid)

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

# well as much as users join the live_data_room on join we still have to have this optional join option here
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


async def leave_live_data_room(sid):
    """
    allow clients to optionaly leave a live data room
    """
    try:
        await sio_server.leave_room(sid, LIVE_MATCHES_ROOM_ID)
        logger.info(f"an error occured whle trying to leave room : {LIVE_MATCHES_ROOM_ID}")

    except Exception as e:

        logger.error(f"an error occured while trying to leave live room: {str(e)}",
        exc_info=True,
        extra={"sid": sid})

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to leave live data room"
        )