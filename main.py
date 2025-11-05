from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pytz import timezone
import os
from dotenv import load_dotenv
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import sys

from api.utils.dependancies import db_dependancy
from db.db_setup import Base, engine, get_db
from db.db_setup import create_database, drop_database
from api import api_auth, api_users, api_transactions, api_fixtures
from api.admin_routes.admin_apis import leagues, fixtures
from logging_config import setup_logging
from services.polling_services.polling_client import schedule_daily_polling, should_start_polling_now, polling_manager
from services.sockets.socket_services import sio_app

# Define timezone
NAIROBI_TZ = timezone('Africa/Nairobi')

app = FastAPI()

app.mount('/socket_services', app=sio_app)

load_dotenv('.env')
load_dotenv('.env.prod')

allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('The application has just started')
    
    setup_logging()

    """
    # APScheduler initialization
    scheduler = AsyncIOScheduler(timezone=NAIROBI_TZ)
    scheduler.start()
    logger.info("APScheduler started")

    # Schedule the 1 PM daily trigger
    schedule_daily_polling(scheduler)

    # Check if we should start polling immediately
    if should_start_polling_now():
        now = datetime.now(NAIROBI_TZ)
        logger.info(f"Current time: {now.strftime('%H:%M')} is within polling hours, starting immediately")
        
        # Get database session for polling
        async for db in get_db():
            try:
                await polling_manager.start(db)
                break  # Only need one session
            except Exception as e:
                logger.error(f"Failed to start polling: {str(e)}", exc_info=True)
            finally:
                await db.close()
    else:
        logger.info("Outside polling hours, waiting for 1pm to 3am polling window")

    """

    yield  # Application is running

    """

    # On application shutdown
    print('The application is shutting down now')

    # Stop polling gracefully
    await polling_manager.stop()

    # Shut down the scheduler
    scheduler.shutdown(wait=True)
    logger.info("APScheduler shutdown")
    logger.info("Application shutdown complete")
    """


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
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
app.include_router(fixtures.router)