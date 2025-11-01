import redis
from fastapi import HTTPException, status

# connect to redis
# redis is runnig localy on my system , on production we might want to think of using the redis caching service
r= redis.Redis(
    host='localhost',
    port =6379,
    password='1423Okello,',
    decode_responses=True, # this is a must to avoid getting coroutine objects as responses
    db=1
)

# popular leageus will be added to redis on startup
# this will always be called on startup of the application
async def add_popular_leagues_to_redis():
    pass

# we will use the popular leagues id for processing match data from the api
async def get_popular_league_ids_from_redis():
    # find a way to make this return a list of id's of live matches as its return object
    pass

# we will use this when processing data live league data from the api
async def get_live_matches_from_redis():
    pass

# for adding live matches to redis
async def add_live_match_to_redis():
    ...