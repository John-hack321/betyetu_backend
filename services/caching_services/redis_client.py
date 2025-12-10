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
    port =6379,
    password='1423Okello,',
    decode_responses=True, # this is a must to avoid getting coroutine objects as responses
    db=1
)

r2= redis.Redis(
    host='localhost',
    port =6379,
    password='1423Okello,',
    decode_responses=True,
    db=2
)

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
        r.hset("live_matches",
        str(redis_live_match.matchId),
        redis_live_match.json())

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


# ALTERNATIVE MATCH HANDLING FUNCTIONS

# functinalitis for the alternative match handling
async def cache_todays_matches(db: AsyncSession):
    """
    we will be caching todays matches for efficient accesst to them 
    """

    try :

        db_todays_matches= await get_todays_matches(db)

        if not db_todays_matches:
            logger.info(f"we were unable to get todays matches from the db")
            db_todays_matches= []  # make it to be just an empty object now so that the programm does not fail.

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
    try :

        r.hdel('live-matches', match_id)
        print(f"match of id : {match_id} has been deleted from the redis store")
    
    except Exception as e:

        logger.error(f"an error occured while trying to remove match from the redis store")

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to remove match from redis store: {str(e)}"
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
    print(f"updating live match away score of match id : {match_id}")
    try:
        match_json= r.hget('live_matches', str(match_id))

        if match_json:
            match_data= json.loads(match_json)
            match_data['awayTeamScore'] = away_score
            r.hset('live_matches', str(match_id), json.dumps(match_data))

    except Exception as e:
        logger.error(f"an error occured while updating the live match away score: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating live match away_score, {str(e)}"
        )