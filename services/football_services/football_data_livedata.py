import logging
import os
from dotenv import load_dotenv
import aiohttp

from fastapi import HTTPException
from fastapi import status

from pydantic_schemas.live_data import LiveFootballDataResponse
from services.caching_services.redis_client import get_live_matches_from_redis, get_popular_league_ids_from_redis

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



    async def __process_live_football_data(self, live_football_data: LiveFootballDataResponse):
        popular_league_ids: list[int]= await get_popular_league_ids_from_redis()
        cached_live_matches= await get_live_matches_from_redis()

        for item in live_football_data.response:
            if item.leagueId in popular_league_ids:
                pass
            continue