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
from api import api_auth, api_users, api_transactions, api_fixtures, api_leagues, api_stakes
from api.admin_routes.admin_apis import leagues, fixtures, stakes
from logging_config import setup_logging
from services.polling_services.polling_client import schedule_daily_polling, should_start_polling_now, polling_manager
from services.sockets.socket_services import sio_app
from services.caching_services.redis_client import add_popular_leagues_to_redis

from db.models.model_seasons import Season  # FIRST
from db.models.model_leagues import League, PopularLeague  # SECOND
from db.models.model_teams import Team  # THIRD
from db.models.model_players import Player  # Can be anywhere
from db.models.model_fixtures import Fixture  # FOURTH - depends on Season
from db.models.model_users import User, Account, Transaction, Admin  # FIFTH
from db.models.model_stakes import Stake  # LAST - depends on User and Fixture


# Define timezone
NAIROBI_TZ = timezone('Africa/Nairobi')

load_dotenv('.env')
load_dotenv('.env.prod')

allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('The application has just started')
    
    setup_logging()
    
    # ✅ Add popular leagues to Redis on startup - Let get_db() manage session
    async for db in get_db():
        try:
            # await add_popular_leagues_to_redis(db)
            logger.info("Successfully added popular leagues to Redis cache on startup")
        except Exception as e:
            logger.error(f"Failed to add popular leagues to Redis on startup: {str(e)}", exc_info=True)
        break  # ✅ Exit loop - get_db() handles cleanup automatically
    
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
        
        # ✅ Get database session for polling - Let get_db() manage session
        async for db in get_db():
            try:
                #  await polling_manager.start(db)
                pass
            except Exception as e:
                logger.error(f"Failed to start polling: {str(e)}", exc_info=True)
            break  # ✅ Exit loop - get_db() handles cleanup automatically
    else:
        logger.info("Outside polling hours, waiting for 1pm to 3am polling window")

    yield  # Application is running

    # On application shutdown
    print('The application is shutting down now')

    # Stop polling gracefully
    await polling_manager.stop()

    # Shut down the scheduler
    scheduler.shutdown(wait=True)
    logger.info("APScheduler shutdown")
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

app.mount('/socket_services', app=sio_app)

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
app.include_router(api_leagues.router)
app.include_router(api_stakes.router)
app.include_router(stakes.router)