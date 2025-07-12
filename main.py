import fastapi
from fastapi import APIRouter , FastAPI
from fastapi.middleware.cors import  CORSMiddleware

from db.db_setup import Base , engine
from db.db_setup import create_database , drop_database
from api import  api_auth

app = FastAPI(
    # we will add system info here for later on 
)

@app.on_event("startup")
async def startup_event():
    await create_database()

# Base.metadata.create_all(bind = engine) # we had to cancel this out because its not async capable its only fo syncronous databases 

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials = True,
    allow_headers = ['*'],
    allow_methods = ['*'],
)

app.include_router(api_auth.router)
