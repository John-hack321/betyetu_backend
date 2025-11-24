import logging
import os
from dotenv import load_dotenv
import aiohttp
import sys

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_routes.util_matches import update_fixture_to_live_on_db, update_match_with_match_ended_data
from api.utils.util_stakes import get_stake_by_match_id_from_db
from pydantic_schemas.live_data import LiveFootballDataResponse, RedisStoreLIveMatch
from services.caching_services.redis_client import add_live_match_to_redis, get_live_match_data_from_redis, get_live_matches_from_redis, get_popular_league_ids_from_redis, update_live_match_home_score, update_live_match_away_score, update_live_match_time
from services.sockets.socket_services import send_live_data_to_users, update_match_to_live_on_frontend_with_live_data_too
from services.football_services.football_data_api import football_data_api_service

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
        self.football_data_api_key = os.getenv('FOOTBALL_API_KEY')
        self.livefootball_data_api_url = os.getenv('LIVE_FOOTBALL_API_URL')
    
    async def get_live_football_data(self, api_key: str):
        """
        Public method to fetch live football data
        """
        return await self.__fetch_live_football_data(api_key)
    
    async def process_live_football_data(self, live_data: dict , db: AsyncSession):
        """
        Process the live football data
        """
        validated_data= LiveFootballDataResponse(**live_data)
        return await self.__process_live_football_data(validated_data, db)

    async def __fetch_live_football_data(self, api_key: str):
        try:
            headers= {
                "x-rapidapi-key": f"{api_key}",
                "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.livefootball_data_api_url, headers=headers) as response:
                    logger.info(f'the api call was succesful')
                    response_data= await response.json()
                    print(f'the response of live football data gotten back from the api is {response_data}')
                    return response_data
    
        except Exception as e:
            logger.error(f"the live data api fetch failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"an error occured while fetching the live football match data")

    async def __update_match_to_live_on_db_and_frontend(self, db: AsyncSession, match_id: int):
        try:
            await update_fixture_to_live_on_db(db,match_id)
            
            # the match is already updated on db and now we need to do the same on frontend
            await update_match_to_live_on_frontend_with_live_data_too(match_id)

        except HTTPException:
            raise # reraise any excpetion

        except Exception as e:
            logger.error(f'an error occured while updating match to live on db {str(e)}',
            exc_info=True,
            extra={
                "affected_match_id": match_id
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occured while updating match to live on db and frontend, {str(e)}"
            )


    async def __process_matches_that_have_ended(self, db: AsyncSession, updated_match_ids_list: list[int]):
        try:
            live_matches_list: list[RedisStoreLIveMatch]= await get_live_matches_from_redis()
            for item in live_matches_list:
                if item.matchId in updated_match_ids_list:
                    # it is in the updated match ids list then it means that it is still live
                    # if not it means that it has ended and we will query the data from the api and update it on the backend
                    continue
                # the first usage of the global football_data_service
                
                # TODO: define a pydantic fixture for this match end model from the api
                # TODO: define the functionality for getting the matches by match id from the api
                fixture= await football_data_api_service.__get_fixture_by_match_id(item.matchId) # this is an api call to the football data service
                db_fixture_object= await update_match_with_match_ended_data(db, fixture)

                # I think we also need to update the stakes with the winner of the matches and all right ? and also dispatch money based on who has won or ?
                # get stake by match id 
                # update the data based on the match outcome
                # process the win and update account balance of the winner with the possible win amount
                
                # get stake by match id from the database

                # updating of data based on fixture scores
                match_scores= await football_data_api_service.get_match_scores_by_match_id(item.matchId)
                                

                if not db_fixture_object:
                    logger.error(f"failed to update fixture objecct to ended status in db")

                # the next step is to make the fronted to be aware of this specific one


        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"an error occured while processing matches that have ended: {str(e)}",
            exc_info=True,
            extra={})
        


    # this functio will be called everytime we get live data back from api calls
    # it has no return type as it is a process function
    async def __process_live_football_data(self, live_football_data: LiveFootballDataResponse, db: AsyncSession):
        """
        first check matchi is in a popular league
        if it is not add to the redis store
        if it is in a populare league, compare if the scores have changed
        """

        try:
            popular_league_ids: list[int]= await get_popular_league_ids_from_redis()

            updated_match_ids_list= []

            if len(live_football_data.response) == 0:
                return # we return early if there are no live matches at the moment

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
                        await self.__update_match_to_live_on_db_and_frontend(db, item.id)
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

            # i think we can also use the updated_match_ids_list to know which matches are in the store but no in the live_data
            # these are the matches that we need to handle by updating them on db as ended and on user also as ended and remove them from redis to
            
            await self.__process_matches_that_have_ended()

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

# i think i should make the live data service instance global
# thought i havent used it as a global thing yet in the code 
# but im about to soon so long as im done with the consulting on whether to use it or not
live_data_service= LiveDataService()