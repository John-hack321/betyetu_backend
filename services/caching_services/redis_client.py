import sys
import json
from aiohttp import http_exceptions
import redis
from fastapi import HTTPException, status
from pydantic import BaseModel

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_routes.util_leagues import get_popular_leageus_ids_from_db
from api.admin_routes.util_matches import get_todays_matches
from db.models.model_fixtures import FixtureStatus
from pydantic_schemas.live_data import RedisStoreLiveMatch
from pydantic_schemas.live_data import RedisStoreLiveMatchVTwo

from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

# redis is runnig localy on my system , on production we might want to think of using the redis caching service
r= redis.Redis(
    host='localhost',
    port =6380,
    password='1423Okello,',
    decode_responses=True, # this is a must to avoid getting coroutine objects as responses
    db=1
)

r2= redis.Redis(
    host='localhost',
    port =6380,
    password='1423Okello,',
    decode_responses=True,
    db=2
)

# FOR THE OLD POLLING LOOP LOGIC: STARTS HERE

# popular leageus will be added to redis on startup
# this will always be called on startup of the application
async def add_popular_leagues_to_redis(db: AsyncSession):
    try:
        league_ids_list: list[int]= await get_popular_leageus_ids_from_db(db)

        r2.json().set('league_ids_cache', '$', {
        'league_ids': league_ids_list
        })

        return {
            'status': status.HTTP_200_OK,
            'message': "the league data has been added succesfully the database",
            }

    except Exception as e:
        logger.error(f"an error occured while adding league data to redis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an error occured while adding league ids to the redis cache")

# we will use the popular leagues id for processing match data from the api
async def get_popular_league_ids_from_redis():
    try:
        league_ids_list= r2.json().get('league_ids_cache', '$.league_ids')
        print(f"the data league ids  gotten back from redis is : {league_ids_list}")
        return league_ids_list
    except Exception as e:
        logger.error(f"an error occured while trying to fethc league ids from the redis cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while fetching adding league id data to the redis store number 2"
        )

# we will use this when processing data live league data from the api
async def get_live_matches_from_redis():
    print(f"the get live matches function from redis is now running")
    try:
        live_matches_list= r.hgetall('live_matches')
        print(f"matches gotten from redis are: {live_matches_list}")
        return live_matches_list
    except Exception as e:
        logger.error(f"an error occured while getting live matches from redis, detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an error occured while trying to get live data from redis")

async def get_live_match_data_from_redis(match_id: str):
    print(f"running the get_live_mtch_data_from_redis function with match_id: {match_id}")
    try:
        live_match= r.hget('live_matches', str(match_id))
        return live_match
    except Exception as e:
        logger.error(f"an error occured while fetching live match from redis stor r: detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while fetching match from redis store, {str(e)}"
        )

# for adding live matches to redis
async def add_live_match_to_redis(redis_live_match: RedisStoreLiveMatch):
    try:
        match_data = redis_live_match.model_dump()
        match_id = match_data.get('matchId')
        
        # Add current timestamp to the match data
        match_data['timestamp'] = datetime.utcnow().isoformat()
        
        # We will use the match id as the key and store the match data as a JSON string
        r.hset('live_matches', str(match_id), json.dumps(match_data, default=str))

        return {
            'status': status.HTTP_200_OK,
            'message': "match has been added successfuly",
        }

    except Exception as e:
        logger.error(f"error while adding match to the redis store: r, detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while adding the live match data to the redis store man"
        )



async def update_live_match_time(match_id: int, time: str):
    print(f"updating live match time of match id : {match_id}")
    try:
        match_json= r.hget('live_matches', str(match_id))

        if match_json:
            match_data= json.loads(match_json)
            match_data['time']= time
            r.hset('live_matches', str(match_id), json.dumps(match_data))

    except Exception as e:
        logger.error(f"an error occured while updating the live match timer")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating the timer for the live match data"
        )

# OLD POLLING LOOP MATCH REDIS LOGIC END HERE 


# ALTERNATIVE MATCH HANDLING FUNCTIONS

# functinalitis for the alternative match handling
async def cache_todays_matches(db: AsyncSession):
    """
    Cache today's matches in Redis for efficient access.
    
    This function will first flush all existing matches from the Redis store
    before adding the current day's matches to ensure we don't have stale data.
    """
    try:
        # First, flush all existing matches to ensure a clean slate
        logger.info("Flushing existing matches from Redis store before caching today's matches")
        flush_all_matches()
        
        # Get today's matches from the database
        db_todays_matches = await get_todays_matches(db)

        if not db_todays_matches:
            logger.info("No matches found in the database for today")
            return True  # Return success but with no matches to cache

        logger.info(f"Caching {len(db_todays_matches)} matches in Redis")
        
        for item in db_todays_matches:

            # so the matches are set into the redis store using their match ids as the id that will be used for querying them if qurying will be necesary at one point
            match_date_str = item.match_date.isoformat() if item.match_date else ""

            item= RedisStoreLiveMatchVTwo(
                matchId= str(item.match_id),
                leagueId= str(item.league_id),
                homeTeam= item.home_team,
                awayTeam= item.away_team,
                homeTeamScore= item.home_score,
                awayTeamScore= item.away_score,
                date= match_date_str,
                time= "",
                fixtureStatusInDb= FixtureStatus.future, # will be set to futre by default and manipulated along the way as we handle the match data on the go
            )

            r.hset("live_matches",
            str(item.matchId),
            item.json())

        return True

    except HTTPException:
        # rethrow these ones
        pass


    except Exception as e:

        logger.error(f"an error occured while trying to query matches from the db, detail= {str(e)}")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to cache todays matches in the redis cache, {str(e)}"
        )


async def get_cached_matches() -> list[RedisStoreLiveMatchVTwo]:
    """
    returns a parsed list of the live matches store on redis: NOTE: not all of the matches are live
    """
    try:
        redis_live_matches= r.hgetall('live_matches')
        
        redis_matches_list: list[RedisStoreLiveMatchVTwo] = []

        for match_id, match_json in redis_live_matches.items():
            match_data= json.loads(match_json)

            redis_match= RedisStoreLiveMatchVTwo(**match_data)

            redis_matches_list.append(redis_match)

        print('the matches gotten from the redis store are')
        for match in redis_matches_list:
            print(f"{match.matchId}")

        return redis_matches_list

    except Exception as e:
        logger.error(f"an error occured while getting the cached matches, {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to get cached matches from the redis stroe , {str(e)}"
        )

async def remove_match_from_redis_redis_store(match_id: str):
    try:
        # Using consistent key name with underscore to match other functions
        r.hdel('live_matches', match_id)
        logger.info(f"Match ID {match_id} has been deleted from the redis store")
    
    except Exception as e:
        error_msg = f"An error occurred while trying to remove match {match_id} from the redis store: {str(e)}"
        logger.error(error_msg)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

async def update_live_match_time(match_id: int, time: str):
    print(f"updating live match time of match id : {match_id}")
    try:
        match_json= r.hget('live_matches', str(match_id))

        if match_json:
            match_data= json.loads(match_json)
            match_data['time']= time
            r.hset('live_matches', str(match_id), json.dumps(match_data))

    except Exception as e:
        logger.error(f"an error occured while updating the live match timer")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating the timer for the live match data"
        )


# UNIVERSAL HELPER FUNCTIONS
# these ones work for both approaches of the live data service

async def update_live_match_home_score(match_id: int, home_score: int):
    print(f"updating live match home score of match id : {match_id}")
    try:
        match_json = r.hget("live_matches", str(match_id))
        
        if match_json:
            # Parse, update, and save back
            match_data = json.loads(match_json)
            match_data['homeTeamScore'] = home_score
            r.hset("live_matches", str(match_id), json.dumps(match_data))

    except Exception as e:
        logger.error(f"an error occured while updating the home score of a live match, {str(e)}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"an error occured while updating the live match {str(e)}")

async def update_live_match_away_score(match_id: int, away_score: int):
    try:
        # Get the current match data
        match_data = r.get(f"live_match:{match_id}")
        if match_data:
            match_dict = json.loads(match_data)
            # Update the away score
            match_dict['away_score'] = away_score
            # Save back to Redis
            r.set(f"live_match:{match_id}", json.dumps(match_dict))
            logger.info(f"Updated away score for match {match_id} to {away_score}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating away score for match {match_id}: {str(e)}")
        return False


async def cleanup_old_matches(hours_old: int = 2):
    """
    Remove matches from Redis that are older than the specified hours.
    
    Args:
        hours_old: Number of hours after which a match is considered old
    """
    try:
        # Get all matches from Redis
        all_matches = r.hgetall("live_matches")
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
        removed_count = 0
        
        logger.info(f"🧹 Starting cleanup of matches older than {hours_old} hours")
        logger.info(f"⏰ Cutoff time: {cutoff_time.isoformat()}")
        
        for match_id, match_json in all_matches.items():
            try:
                match_data = json.loads(match_json)
                
                # Check if match has a timestamp
                if 'timestamp' in match_data:
                    match_time = datetime.fromisoformat(match_data['timestamp'])
                    
                    if match_time < cutoff_time:
                        r.hdel("live_matches", match_id)
                        removed_count += 1
                        logger.info(f"🗑️  Removed old match {match_id} (timestamp: {match_time.isoformat()})")
                
                # Also check match date
                elif 'date' in match_data:
                    match_date = datetime.fromisoformat(match_data['date'])
                    
                    if match_date < cutoff_time:
                        r.hdel("live_matches", match_id)
                        removed_count += 1
                        logger.info(f"🗑️  Removed old match {match_id} (date: {match_date.isoformat()})")
                        
            except Exception as e:
                logger.error(f"❌ Error processing match {match_id}: {str(e)}")
                continue
        
        logger.info(f"✅ Cleanup complete: Removed {removed_count} old matches from Redis")
        return removed_count
        
    except Exception as e:
        logger.error(f"❌ Error in cleanup_old_matches: {str(e)}", exc_info=True)
        return 0


async def flush_all_matches():
    """
    Manually flush all matches from Redis.
    Use with caution - this removes ALL match data.
    """
    try:
        r.delete("live_matches")
        logger.info("🗑️  Flushed all matches from Redis")
        return True
    except Exception as e:
        logger.error(f"❌ Error flushing matches: {str(e)}")
        return False


async def cleanup_old_matches(hours_old: int = 2):
    """
    Remove matches from Redis that are older than the specified hours.
    
    Args:
        hours_old: Number of hours after which a match is considered old
    """
    try:
        # Get all match keys
        match_keys = r.keys("live_match:*")
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
        removed_count = 0
        
        for key in match_keys:
            try:
                match_data = r.get(key)
                if match_data:
                    match_dict = json.loads(match_data)
                    # Check if match has a timestamp and is older than cutoff
                    if 'timestamp' in match_dict:
                        match_time = datetime.fromisoformat(match_dict['timestamp'])
                        if match_time < cutoff_time:
                            r.delete(key)
                            removed_count += 1
            except Exception as e:
                logger.error(f"Error processing match key {key}: {str(e)}")
                continue
                
        logger.info(f"Cleaned up {removed_count} old matches from Redis")
        return removed_count
    except Exception as e:
        logger.error(f"Error in cleanup_old_matches: {str(e)}")
        return 0