import fastapi
from fastapi import  FastAPI
from fastapi.middleware.cors import  CORSMiddleware

import os
from dotenv import load_dotenv

from db.db_setup import Base , engine
from db.db_setup import create_database , drop_database
from api import  api_auth , api_users , api_transactions , api_chess_foreign

app = FastAPI(
    # we will add system info here for later on 
)

load_dotenv('.env')
load_dotenv('.env.prod') # as always this one overides the first .env file 

# In main.py, update this line:
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')


# we dont need this anymore alembic will handle the creations 
"""
@app.on_event("startup")
async def startup_event():
    # await drop_database()  # This will drop all tables
    await create_database()  # This will recreate them
"""
# Base.metadata.create_all(bind = engine) # we had to cancel this out because its not async capable its only fo syncronous databases 

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_headers=['*'],
    allow_methods=['*'],
    expose_headers=['*'],
)

app.include_router(api_auth.router)
app.include_router(api_users.router)
app.include_router(api_transactions.router)
app.include_router(api_chess_foreign.router)