from aiohttp import http_exceptions
import redis
from fastapi import HTTPException, status
from pydantic import BaseModel

import logging

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
async def add_popular_leagues_to_redis(popular_league_ids: list[int]):
    try:
        r2.json().set('league_ids_cache', '$', {
        'league_ids': popular_league_ids
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
        return league_ids_list
    except Exception as e:
        logger.error(f"an error occured while trying to fethc league ids from the redis cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while fetching adding league id data to the redis store number 2"
        )

# we will use this when processing data live league data from the api
async def get_live_matches_from_redis():
    pass

# for adding live matches to redis
async def add_live_match_to_redis():
    ...