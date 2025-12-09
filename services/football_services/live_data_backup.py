import logging
import os
from dotenv import load_dotenv
import aiohttp

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.caching_services.redis_client import cache_todays_matches

load_dotenv()


logger= logging.getLogger(__name__)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
class LiveDataServiceBackup():
    def __init__(self):
        self.football_data_api_key = os.getenv('FOOTBALL_API_KEY')
        self.api_host= os.getenv('API_HOST')
        self.match_score_url= os.getenv('MATCH_SCORE_URL')


    async def put_todays_matches_on_redis(db: AsyncSession):
        try:

            result= await cache_todays_matches(db)

            if result == False:
                logger.info(f"the additon of the matches to the endpont has failed")

            logger.info(f"the matches have been succesfuly set to the redis store")

        except HTTPException:
            raise
        
        except Exception as e:
            logger.error(f"an error occured while putting todays matches on redis, {str(e)}")

            raise HTTPException(
                status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occured while putting the matches to the redis store, {str(e)}"
            )


    async def get_match_score_detais(self, match_id: str):

        headers = {
        'x-rapidapi-key': self.football_data_api_key,
        'x-rapidapi-host': self.api_host
        }

        url= f"self.match_score_url{match_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        response_data= await response.json()
                        return response_data

                    else:
                        logger.error(f"Error occured: {response.status}")
                        return None

        except Exception as e:
            logger.error(f" an error occured while trying to fetch match score data from the api endpoint, {str(e)}")

            raise HTTPException(
                status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                datail= f"an error occured while fetching match score data from the api endpont: {str(e)}"
            )


    async def handle_matches_iteration():
        """
        fetch the matches from redis
        iterate through them one by one confirming the time on them by comparing to the tiem with a backlogo f upto 2 hours like on the db
        if the match is marked as endend do necesary update and remove it from the redis store
        else we upate the scores if any, push the update to the database and the frontend if possible
        if the match has just startedn mark it as live on the db too
        """

liveDataBackup= LiveDataServiceBackup()