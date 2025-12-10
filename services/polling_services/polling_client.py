import asyncio
from datetime import datetime, timedelta
from fastapi import HTTPException, status

import logging
import sys
from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import AsyncSession

from pydantic_schemas.live_data import RedisStoreLiveMatchVTwo
from services.caching_services.redis_client import get_cached_matches
from services.football_services.live_data_backup import LiveDataServiceBackup, liveDataBackup

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

logger = logging.getLogger(__name__)
load_dotenv()


class PollingManager():
    """
    Manages the live data polling service with intelligent resource optimization.
    Only polls actively when matches are imminent or live.
    """
    def __init__(self):
        self.current_task = None
        self.live_data_service_backup = LiveDataServiceBackup()
        self.football_data_api_key = os.getenv("FOOTBALL_API_KEY")
        self.matches_cached = False
        self.PRE_MATCH_BUFFER_MINUTES = 30  # Start polling 30 mins before first match

    def is_running(self):
        """Check if polling task is currently running"""
        return self.current_task and not self.current_task.done()

    async def start(self, db: db_dependancy):
        """Start the polling manager"""
        if self.is_running():
            logger.warning("Polling already running, ignoring start request")
            return

        logger.info("Starting live data polling manager")
        
        # Cache matches if not already done
        if not self.matches_cached:
            try:
                logger.info("Caching today's matches to Redis...")
                await liveDataBackup.put_todays_matches_on_redis(db)
                self.matches_cached = True
                logger.info("✓ Matches successfully cached to Redis")
            except Exception as e:
                logger.error(f"Failed to cache matches: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error caching matches: {str(e)}"
                )

        self.current_task = asyncio.create_task(self._poll_loop(db))

    async def stop(self):
        """Stop polling gracefully"""
        if self.current_task and not self.current_task.done():
            logger.info("Stopping polling task...")
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                logger.info("✓ Polling task cancelled successfully")

    async def _calculate_sleep_until_first_match(self, redis_matches: list[RedisStoreLiveMatchVTwo]) -> int:
        """
        Calculate optimal sleep time until first match.
        Returns sleep seconds, or 0 if should start polling immediately.
        """
        if not redis_matches:
            logger.info("No matches in Redis, no need to poll")
            return -1  # Signal to exit

        now = datetime.now(NAIROBI_TZ).replace(tzinfo=None)
        
        # Find earliest match time
        earliest_match_time = None
        for match in redis_matches:
            try:
                match_date = datetime.fromisoformat(match.date)
                if earliest_match_time is None or match_date < earliest_match_time:
                    earliest_match_time = match_date
            except Exception as e:
                logger.error(f"Error parsing match date for {match.matchId}: {str(e)}")
                continue

        if earliest_match_time is None:
            logger.warning("Could not determine earliest match time")
            return 0  # Start polling immediately as fallback

        # Calculate time until match
        time_until_match = earliest_match_time - now
        minutes_until_match = time_until_match.total_seconds() / 60

        logger.info(f"📅 Earliest match at: {earliest_match_time.strftime('%H:%M:%S')}")
        logger.info(f"⏰ Current time: {now.strftime('%H:%M:%S')}")
        logger.info(f"⏳ Time until match: {int(minutes_until_match)} minutes")

        # If match has already started or is within buffer time, start immediately
        if minutes_until_match <= self.PRE_MATCH_BUFFER_MINUTES:
            logger.info(f"✓ Match starting soon or already started, beginning active polling")
            return 0

        # Calculate sleep time (wake up buffer minutes before match)
        sleep_minutes = minutes_until_match - self.PRE_MATCH_BUFFER_MINUTES
        sleep_seconds = int(sleep_minutes * 60)

        logger.info(f"💤 Sleeping for {int(sleep_minutes)} minutes until {self.PRE_MATCH_BUFFER_MINUTES} mins before match")
        logger.info(f"⏰ Will resume polling at approximately: {(now + timedelta(seconds=sleep_seconds)).strftime('%H:%M:%S')}")
        
        return sleep_seconds

    async def _check_if_all_matches_processed(self, redis_matches: list[RedisStoreLiveMatchVTwo]) -> bool:
        """
        Check if all cached matches have been processed (finished).
        Returns True if we can stop polling early.
        """
        if not redis_matches:
            logger.info("📭 No matches remaining in Redis cache")
            return True

        now = datetime.now(NAIROBI_TZ).replace(tzinfo=None)
        cutoff_time = now - timedelta(hours=2)

        # Check if any matches are still relevant (not older than 2 hours)
        relevant_matches = 0
        for match in redis_matches:
            try:
                match_date = datetime.fromisoformat(match.date)
                if match_date >= cutoff_time:
                    relevant_matches += 1
            except Exception as e:
                logger.error(f"Error checking match {match.matchId}: {str(e)}")
                continue

        if relevant_matches == 0:
            logger.info("✓ All matches processed (all older than 2 hours)")
            return True

        logger.info(f"📊 {relevant_matches} matches still being tracked")
        return False

    async def _poll_loop(self, db: AsyncSession):
        """
        Optimized polling loop with intelligent sleep/wake cycles.
        Only actively polls when matches are imminent or live.
        """
        logger.info("=" * 60)
        logger.info("🚀 POLLING LOOP STARTED")
        logger.info("=" * 60)

        try:
            # Initial check: should we sleep until first match?
            redis_matches = await get_cached_matches()
            sleep_seconds = await self._calculate_sleep_until_first_match(redis_matches)

            if sleep_seconds == -1:
                logger.info("No matches to poll, exiting")
                return

            if sleep_seconds > 0:
                logger.info(f"💤 Initial sleep: {sleep_seconds} seconds ({sleep_seconds/60:.1f} minutes)")
                await asyncio.sleep(sleep_seconds)
                logger.info("⏰ Waking up - starting active polling phase")

            # Active polling phase
            iteration_count = 0
            consecutive_empty_iterations = 0
            MAX_EMPTY_ITERATIONS = 5  # Stop if no matches for 5 iterations

            while True:
                try:
                    now = datetime.now(NAIROBI_TZ)
                    iteration_count += 1

                    logger.info("-" * 60)
                    logger.info(f"🔄 ITERATION #{iteration_count} - {now.strftime('%H:%M:%S')}")
                    logger.info("-" * 60)

                    # Check if we've passed 3 AM cutoff
                    if now.hour >= 3 and now.hour < 13:
                        logger.info(f"⏰ Reached 3 AM cutoff (current: {now.hour}:00)")
                        logger.info("🛑 Stopping polling until next scheduled run at 1 PM")
                        break

                    # Get current matches and check if all processed
                    redis_matches = await get_cached_matches()
                    
                    if await self._check_if_all_matches_processed(redis_matches):
                        consecutive_empty_iterations += 1
                        logger.info(f"📭 No active matches ({consecutive_empty_iterations}/{MAX_EMPTY_ITERATIONS})")
                        
                        if consecutive_empty_iterations >= MAX_EMPTY_ITERATIONS:
                            logger.info("=" * 60)
                            logger.info("✅ ALL MATCHES PROCESSED - EARLY TERMINATION")
                            logger.info(f"📊 Total iterations completed: {iteration_count}")
                            logger.info(f"⏰ Stopped at: {now.strftime('%H:%M:%S')}")
                            logger.info("🛑 Polling will resume tomorrow at 1 PM")
                            logger.info("=" * 60)
                            break
                    else:
                        consecutive_empty_iterations = 0  # Reset counter

                    # Process matches
                    try:
                        await liveDataBackup.handle_matches_iteration(redis_matches, db)
                        logger.info(f"✓ Iteration #{iteration_count} completed successfully")
                    except Exception as e:
                        logger.error(f"❌ Error in iteration #{iteration_count}: {str(e)}", exc_info=True)
                        # Continue polling despite errors

                    # Sleep before next iteration
                    logger.info(f"💤 Sleeping 60 seconds before next iteration...")
                    await asyncio.sleep(60)

                except asyncio.CancelledError:
                    logger.info("🛑 Polling loop cancelled")
                    raise
                except Exception as e:
                    logger.error(f"❌ Error in polling iteration: {str(e)}", exc_info=True)
                    await asyncio.sleep(60)  # Continue after error

        except asyncio.CancelledError:
            logger.info("🛑 Polling loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in polling loop: {str(e)}", exc_info=True)
        finally:
            logger.info("=" * 60)
            logger.info("🏁 POLLING LOOP TERMINATED")
            logger.info(f"📊 Final iteration count: {iteration_count if 'iteration_count' in locals() else 0}")
            logger.info(f"⏰ Terminated at: {datetime.now(NAIROBI_TZ).strftime('%H:%M:%S')}")
            logger.info("=" * 60)


# Global polling manager instance
polling_manager = PollingManager()


def schedule_daily_polling(scheduler: AsyncIOScheduler):
    """
    Schedule polling to start at 1 PM every day.
    Uses cron trigger for precise daily scheduling.
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
                # await db.close()
                pass

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
    logger.info("✓ Scheduled daily polling start at 1:00 PM EAT")


def should_start_polling_now():
    """
    Check if we should start polling immediately on startup.
    Returns True if current time is between 1 PM and 3 AM.
    """
    now = datetime.now(NAIROBI_TZ)
    
    # Between 1 PM (13:00) and midnight
    if 13 <= now.hour <= 23:
        return True
    
    # Between midnight and 3 AM
    if 0 <= now.hour < 3:
        return True

    return False