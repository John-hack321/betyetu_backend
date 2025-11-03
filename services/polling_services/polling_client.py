import asyncio
import datetime
from time import timezone
from fastapi import HTTPException, status, HTTPException

import logging
import sys
from dotenv import load_dotenv
import os

from services.football_services.football_data_livedata import LiveDataService
from apscheduler.schedulers.asyncio import AsyncIOScheduler


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

    # check if theres a task that is running
    def running(self):
        return self.current_task and not self.current_task.done()

    
    # starting the task
    async def start(self):
        if self.is_running():
            logger.warning(f"polling already running, ignoring start request")

        logger.info(f"starting live data polling")
        self.current_task= asyncio.create_task(self._poll_loop())
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


    async def _fetch_and_process_live_football_data(self):
        try:
            logger.info("sending the request for live data now")
            live_data= await self.live_data_service.__fetch_live_football_data()

            logger.info(f"now processing the data")
            await self.live_data_service.__process_live_football_data(live_data)

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

    # the polling loop itself
    async def _poll_loop(self):
        # the main polling loop runs every 7 seconds and self terminates at 3 am
        logger.info(f"the polling loop has been started")

        while True:
            try:
                now= datetime.now(nairobi_tz)

                # check if we have reached 3AM which is the stopping time
                if now.hour >= 3 and now.hour < 13:
                    logger.info(f"reached 3AM stop time {current: {now.hour}:00}, stopping polling")
                    break

                await self._fetch_and_process_live_football_data()

                # sleep for 7 seconds first
                await asyncio.sleep(7)

            except asyncio.CancelledError:
                logger.info(f"Polling loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"an error in polling loop: {str(e)}",
                exc_info=True)

                await asyncio.sleep(7)
                 
                # as much an HTTPException was not raised at this point we aught to have raised one, well i think so
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"error in polling loop: {str(e)}"
                )

# we will maintain a global polling manager instance
polling_manager= PollingManager()

def schedule_daily_polling(scheduler: AsyncIOScheduler):
    """
    schedule polling to start at 1 pm every day
    uses cron trigger for precise daily scheduling
    """

    schedular.add_job(
        polling_manager.start,
        rigger= CronTrigger(
            hour=13,
            minute=0,
            timezone= NAIROBI_TZ
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