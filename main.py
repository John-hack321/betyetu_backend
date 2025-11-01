from contextlib import asynccontextmanager
import fastapi
from fastapi import  FastAPI
from fastapi.middleware.cors import  CORSMiddleware

import os
from dotenv import load_dotenv

from db.db_setup import Base , engine
from db.db_setup import create_database , drop_database
from api import  api_auth , api_users , api_transactions , api_fixtures
from api.admin_routes.admin_apis import leagues
from logging_config import setup_logging


app = FastAPI(
    # we will add system info here for later on 
)

load_dotenv('.env')
load_dotenv('.env.prod') # as always this one overides the first .env file 

# In main.py, update this line:
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')


# we dont need this anymore alembic will handle the creations 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print('the application has just started')

    # on startup config actions
    setup_logging()

    yield # the application is running 

    # on application shuttdown
    print('the application is shutting down now')

# Base.metadata.create_all(bind = engine) # we had to cancel this out because its not async capable its only fo syncronous databases 

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], # for now we will accept all origins the modify later on
    allow_credentials=True,
    allow_headers=['*'],
    allow_methods=['*'],
    expose_headers=['*'],
)

app.include_router(api_auth.router)
app.include_router(api_users.router)
app.include_router(api_transactions.router)
app.include_router(leagues.router)
app.include_router(api_fixtures.router)


