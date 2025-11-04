from contextlib import asynccontextmanager
from fastapi import  FastAPI
from fastapi.middleware.cors import  CORSMiddleware

import os
from dotenv import load_dotenv
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler


from db.db_setup import Base , engine
from db.db_setup import create_database , drop_database
from api import  api_auth , api_users , api_transactions , api_fixtures
from api.admin_routes.admin_apis import leagues
from logging_config import setup_logging
from services.polling_services.polling_client import schedule_daily_polling, should_start_polling_now
from services.sockets.socket_services import sio_app
from services.polling_services.polling_client import polling_manager

app = FastAPI(
    # we will add system info here for later on 
)

app.mount('/socket_services', app=sio_app)

load_dotenv('.env')
load_dotenv('.env.prod') # as always this one overides the first .env file 

# In main.py, update this line:
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)


# handles the startup and shutdonw logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    print('the application has just started')

    # APSchedular initialization logic here
    scheduler= AsyncIOScheduler(timezone= NAIROBI_TZ)
    scheduler.start()
    logger.info("APSschedular started")

    # schedule the 1 pm daily trigger
    schedule_daily_polling(scheduler)

    # check if we should start polling immediately (for a restart scenario)
    if should_start_polling_now():
        now= datetime.now(nairobi_tz)
        logger.info(f"Current time: {now.strftime('%H:%M')} si within polling hours so we are starting immediately")
        await polling_manager.start()

    else:
        logger.info(f"outside polling hors waiting for 1pm to 3 am polling window")

    setup_logging()

    yield # the application is running 

    # on application shuttdown
    print('the application is shutting down now')

    # stop polling gracefully
    await polling_manager.stop()

    # shut down the scheduler
    scheduler.shutdonw(wait=True)
    logger.info(f"APScheduler shutdown")

    logger.info(f"Application shutdown complete")

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