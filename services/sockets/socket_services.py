import socketio
import uuid

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
async def setup_room_id():
    room_id= f"uuid.uuid4()"
    return room_id

# TODO: define a pydantic model for the user_data pyaload for joing a room
async def join_room_for_live_data(user_data):
    await sio_server.enter_room(user_data.get("sid"), user_data.get("room_id"))
    pass

@sio_server.event
async def connect(sid , environ , auth = None):
    print(f'the connection has been established for the sid {sid}')
    await sio_server.emit('join' , {'sid' : sid , 'message': 'Connected successfully'}) 

@sio_server.event
async def disconnect(sid , environ):
    print(f'the sid {sid} as been disconnected')

























"""
this function has not been defined yet, 
its function will be such that any time realtime match data is update 
it will pull the data from redis and send it to the frontend in its entirety
for updates
"""
async def send_match_data_through_socket(match_id: int):
    pass



# designing the socketio room services
# 
# the room will always be accessible to anyone so long that they are logged into the app
# on update of the live match data , the update will be sent to everone connected to the room
# 