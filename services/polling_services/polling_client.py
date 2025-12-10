import asyncio
from datetime import datetime
from time import timezone as std_timezone
from fastapi import HTTPException, status, HTTPException

import logging
import sys
from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import AsyncSession

from pydantic_schemas.live_data import RedisStoreLiveMatchVTwo
from services.caching_services.redis_client import get_cached_matches
from services.football_services import live_data_backup
from services.football_services.football_data_livedata import LiveDataService
from services.football_services.live_data_backup import LiveDataServiceBackup
from services.football_services.live_data_backup import liveDataBackup

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# Define timezone
NAIROBI_TZ = timezone('Africa/Nairobi')
from api.utils.dependancies import db_dependancy



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

load_dotenv()

class PollingManager():
    """
    manages the live data polling service
    ensures that only one polling task is running at a time
    """
    def __init__(self):
        self.current_task= None
        self.live_data_service= LiveDataService()
        self.football_data_api_key= os.getenv("FOOTBALL_API_KEY")
        self.matches_cached= False
        self.live_data_service_backup= LiveDataServiceBackup()
        

    # check if theres a task that is running
    def is_running(self):
        return self.current_task and not self.current_task.done()

    
    # starting the task
    async def start(self, db: db_dependancy):
        if self.is_running():
            logger.warning(f"polling already running, ignoring start request")

        logger.info(f"starting live data polling")
        if not self.matches_cached:
            try :
                logger.info(f"caching matches to redis now")
                await liveDataBackup.put_todays_matches_on_redis(db)
                self.matches_cached= True

            except Exception as e:
                logger.error(f"there was an error caching the matches")

                raise HTTPException(
                    status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail= f"an error occured while trying to cache the matches"
                )

        self.current_task= asyncio.create_task(self._poll_loop(db))
        # and like that we will have created the task and made it to run

    # stoping the polling task
    async def stop(self):
        """top polling gracefully"""
        if self.current_task and not self.current_task.done():
            logger.info(f"stopping the polling taks")
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                logger.info(f"polling task has been cancelled successfully")

    """
        async def _fetch_and_process_live_football_data(self, db: AsyncSession):
            NOTE : these two down here are coments if made to be actvie make sure they are commented 
            fetches live football data from the api endpoint
            proesses the data form the endpoint

            try:
                logger.info("sending the request for live data now")
                # Call the public method that handles the private method call
                live_data = await self.live_data_service.get_live_football_data(self.football_data_api_key)

                if live_data:
                    logger.info("now processing the data")
                    await self.live_data_service.process_live_football_data(live_data, db)

            except Exception:
                raise # raise previouse excpetions

            except HTTPException as e:
                # catch any other httpexception
                logger.error(f"an unxepected error occured while fetching and processing data: {str(e)}",
                exc_info=True,
                extra= {

                })
                
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"an error occured while fetching and processing live data"
                )
    """

    # the polling loop itself
    async def _poll_loop(self, db: AsyncSession):
        # the main polling loop runs every 7 seconds and self terminates at 3 am
        logger.info(f"the polling loop has been started")
        # this is the main loop logic , ti runs every 60 seconds and only stops when 3 am reaches

        iteration_count= 0

        while True:
            try:
                now = datetime.now(NAIROBI_TZ)
                iteration_count += 1
                

                # check if we have reached 3AM which is the stopping time
                if now.hour >= 3 and now.hour < 13:
                    logger.info(f"reached 3AM stop time (current: {now.hour}:00), stopping polling")
                    break

                try:
                    redis_matches_list: list[RedisStoreLiveMatchVTwo]= await get_cached_matches()
                    await liveDataBackup.handle_matches_iteration(redis_matches_list, db)

                    logger.info(f"iteration count {iteration_count} has been completd successfuly")

                except Exception as e:
                    logger.error(f"an error occured while initiating iteration, {str(e)}")

                    raise HTTPException(
                        status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail= f"an error occured while initiating iteration, {str(e)}"
                    )

                # sleep for 7 seconds first
                await asyncio.sleep(60) # this is for dev perposes dont forget to return this to 7 seconds

            except asyncio.CancelledError:
                logger.info(f"Polling loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"an error in polling loop: {str(e)}",
                exc_info=True)

                await asyncio.sleep(60)

# we will maintain a global polling manager instance
polling_manager= PollingManager()

def schedule_daily_polling(scheduler: AsyncIOScheduler):
    """
    Schedule polling to start at 1 pm every day
    Uses cron trigger for precise daily scheduling
    """
    from db.db_setup import get_db

    async def start_polling_job():
        async for db in get_db():
            try:
                await polling_manager.start(db)
                break  # Only need one session
            except Exception as e:
                logger.error(f"Failed to start polling job: {str(e)}", exc_info=True)
            finally:
                await db.close()

    scheduler.add_job(
        start_polling_job,
        trigger=CronTrigger(
            hour=13,
            minute=0,
            timezone=NAIROBI_TZ
        ),
        id="daily_polling_start",
        name="Start Live Data Polling",
        replace_existing=True
    )
    logger.info(f"schedule daily polling start at 1 pm EAT")

def should_start_polling_now():
    """
    check if we shold start polling immediately
    return true if current time is between 1 pm and 3 am
    """

    now= datetime.now(NAIROBI_TZ)
    if 13 <= now.hour<= 23:
        return True
    if 0 <= now.hour < 3:
        return True

    return False