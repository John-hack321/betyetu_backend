import logging
import os
from dotenv import load_dotenv
import aiohttp
import sys

from fastapi import HTTPException
from fastapi import status

from pydantic_schemas.live_data import LiveFootballDataResponse, RedisStoreLIveMatch
from services.caching_services.redis_client import add_live_match_to_redis, get_live_match_data_from_redis, get_live_matches_from_redis, get_popular_league_ids_from_redis, update_live_match_home_score, update_live_match_away_score, update_live_match_time
from services.sockets.socket_services import send_live_data_to_users

# doing better error handling starting from now on this file 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

load_dotenv()
logger= logging.getLogger(__name__)

class LiveDataService():
    def __init__(self):
            self.football_data_api_key= os.getenv('FOOTBALL_API_KEY')
            self.livefootball_data_api_url= os.getenv('LIVE_FOOTBALL_API_URL')

    async def __fetch_live_football_data(self, api_key: str):
        try:
            headers= {
                "x-rapidapi-key": f"{api_key}",
                "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    await response.raise_for_status()
                    logger.info(f'the api call was succesful')
                    response_data= await response.json()
                    return response_data
    
        except Exception as e:
            logger.error(f"the live data api fetch failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"an error occured while fetching the live football match data")


    # this functio will be called everytime we get live data back from api calls
    async def __process_live_football_data(self, live_football_data: LiveFootballDataResponse):
        """
        first check matchi is in a popular league
        if it is not add to the redis store
        if it is in a populare league, compare if the scores have changed
        """

        try:
            popular_league_ids: list[int]= await get_popular_league_ids_from_redis()

            updated_match_ids_list= []

            for item in live_football_data.response:
                if item.leagueId in popular_league_ids:
                    # check if the live match is present in the redis store
                    live_match: RedisStoreLIveMatch= await get_live_match_data_from_redis(item.id)
                    # if the live match is not present we will add it then do other thing necesary for new matches then skip other logic
                    if not live_match:
                        logger.info(f"the live match of id {item.id} is not present in the redis store")
                        live_match_data= RedisStoreLIveMatch(
                            matchId= item.id,
                            leageuId= item.leagueId,
                            homeTeam= item.home.name,
                            awayTeam= item.away.name,
                            homeTeamScore= item.home.score,
                            awayTeamScore= item.away.score,
                            time= item.status.liveTime.short,
                        )
                        await add_live_match_to_redis(live_match_data)
                        continue
                    
                    # confirming to see if there has been a score on both home and away and updating them
                    # on redis and in the same time we also update the time too
                    if item.home.score != live_match.homeTeamScore:
                        await update_live_match_home_score(item.id, item.home.score)
                        update_live_match_time(item.id, item.status.liveTime.short)
                        logger.info('the homve team score has been updated successfuly')
                
                    if item.away.score != live_match.awayTeamScore:
                        await update_live_match_away_score(item.id, item.home.score)
                        update_live_match_time(item.id, item.status.liveTime.short)
                        logger.info(f"the away socre has been updated successfuly")

                    # we will alway updte the live match time even when the other changes have not taken effect
                    update_live_match_time(item.id, item.status.liveTime.short)

                    updated_match_ids_list.append(item.id)

            await send_live_data_to_users(updated_match_ids_list)
            
        except HTTPException:
            raise # reraise the previous exceptionc caught in the dirrerent functoins

        except Exception as e:

            logger.error(f"an error occured while processing live data, {str(e)}",
            exc_info=True, 
            extra={
                "returned_data": live_football_data
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occured while processing live football data, {str(e)}"
            )