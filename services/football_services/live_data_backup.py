import logging
import os
from dotenv import load_dotenv
import aiohttp

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_routes.util_matches import update_fixture_status_in_db, update_home_score_and_away_score_on_db
from api.utils.util_stakes import update_stake_with_winner_data_and_do_payouts
from db.models.model_fixtures import FixtureStatus
from pydantic_schemas.live_data import MatchScoreDetails, ParsedScoreData, RedisStoreLiveMatchVTwo
from services.caching_services.redis_client import cache_todays_matches, remove_match_from_redis_redis_store, update_live_match_away_score, update_live_match_home_score

from datetime import datetime, timedelta
NAIROBI_TZ = timezone('Africa/Nairobi')

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
        """
        I guess it will be wise to do all of the procssing here including the parsing of the data
        """

        headers = {
        'x-rapidapi-key': self.football_data_api_key,
        'x-rapidapi-host': self.api_host
        }

        url= f"{self.match_score_url}{match_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        response_data= await response.json()
                        response_data= MatchScoreDetails(**response_data)

                        # preparing the data we need to return

                        home_score, away_score= map(int, response_data.response.status.scoreStr.split(" - "))
                        parsed_match_scores= ParsedScoreData(
                            homeScore= home_score,
                            awayScore= away_score,
                            finished= response_data.response.status.finished
                        )

                        return parsed_match_scores

                    else:
                        logger.error(f"Error occured: {response.status}")
                        return None

        except Exception as e:
            logger.error(f" an error occured while trying to fetch match score data from the api endpoint, {str(e)}")

            raise HTTPException(
                status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                datail= f"an error occured while fetching match score data from the api endpont: {str(e)}"
            )

    async def handle_matches_iteration(self, redis_matches_list: list[RedisStoreLiveMatchVTwo], db: AsyncSession):
        """
        fetch the matches from redis
        iterate through them one by one confirming the time on them by comparing to the tiem with a backlogo f upto 2 hours like on the db
        if the match is marked as endend do necesary update and remove it from the redis store
        else we upate the scores if any, push the update to the database and the frontend if possible
        if the match has just startedn mark it as live on the db too

        also does payouts at the end too
        """
        try:

            now = datetime.now(NAIROBI_TZ).replace(tzinfo=None)
            cutoff_time = now - timedelta(hours=2)

            logger.info(f"Current time: {now}")
            logger.info(f"Cutoff time: {cutoff_time}")


            for item in redis_matches_list: 

                try:
                    match_date = datetime.fromisoformat(item.date)
        
                    if match_date <= now and match_date >= cutoff_time: # only matches that pass the time comparison will have passed this part
                        # these matches that pass this time check are set to live both on the redis store and on the db
        
                        if item.fixtureStatusInDb == FixtureStatus.future:
                            item.fixtureStatusInDb= FixtureStatus.live
                            await update_fixture_status_in_db(db, item.matchId, FixtureStatus.live)
                            logger.info(f"the status for match of match_id: {item.matchId} as been updated to {FixtureStatus.live}")
        
                        match_score_datails: ParsedScoreData = await self.get_match_score_detais(item.matchId) # this is an API call
        
                        if not match_score_datails: 
                            # if the api call we continue to the next match rather than stopping the whole system
                            continue 
                        
                        if match_score_datails.finished == True:
                            logger.info(f"match of id: {item.matchId} has come back as finished")
        
                            if match_score_datails.homeScore != item.homeTeamScore:
                                item.homeTeamScore= match_score_datails.homeScore
        
                            if match_score_datails.awayScore != item.awayTeamScore:
                                item.awayTeamScore= match_score_datails.awayScore
        
                            # somewhere around here we might maybe need to update the redis store too, but for such ended matches I dont think if its that important
        
                            # if the home score and away score have been upated I belive we will have to do the changes on the db too
        
                            db_match_object= await update_home_score_and_away_score_on_db(
                                db,
                                item.matchId, 
                                match_score_datails.homeScore,
                                match_score_datails.awayScore,
                                FixtureStatus.expired,
                                determine_winner= True)
        
                            if db_match_object:
                                await remove_match_from_redis_redis_store(item.matchId)
        
                                # since match is ended we also have to do the payouts
                                await update_stake_with_winner_data_and_do_payouts(
                                    db, 
                                    item.matchId, 
                                    db_match_object.winner)
        
                        # for matches that have come back as not to have ended ie: live matches
        
                        else: 
                            home_score_updated: bool= False
                            away_score_updated: bool= False
        
                            if match_score_datails.homeScore != item.homeTeamScore:
                                item.homeTeamScore= match_score_datails.homeScore
                                home_score_updated= True
                                await update_live_match_home_score(item.matchId, match_score_datails.homeScore)
        
                            if match_score_datails.awayScore != item.awayTeamScore:
                                item.awayTeamScore= match_score_datails.awayScore
                                away_score_updated= True
                                await update_live_match_away_score(item.matchId, match_score_datails.awayScore)
        
                            if home_score_updated | away_score_updated == True:
                                db_match_object= await update_home_score_and_away_score_on_db(
                                    db, 
                                    item.matchId, 
                                    match_score_datails.homeScore,
                                    match_score_datails.awayScore) # here we wont need to update the fixture status as it is already live and the match isnt ended yet
        
                                # find a way to do update on frontend using web sockets for real time update
                                # await send_update_to_frontend(match_id, match_score_datails.homeScore, match_score_datails.awayScore )
                    
                    elif match_date > now:
                        logger.info(f"✗ Match {item.matchId} hasn't started yet (starts at {match_date})")
                        # Keep in Redis for now
                        continue # we jump to the next match
                        
                    else: 
                        # this one will now occure for matches that started more than 2 hours ago
                        # for them we will aso do a bit of processing to ensure everthing is upto date both on front and back
        
                        match_score_datails: ParsedScoreData = await self.get_match_score_detais(item.matchId) # this is an API call
                        if match_score_datails and match_score_datails.finished:
                            home_score_updated: bool= False
                            away_score_updated: bool= False
        
                            if match_score_datails.homeScore != item.homeTeamScore:
                                item.homeTeamScore= match_score_datails.homeScore # is it realy necesary to update this , I think its just a waste of time right cause its not being used anywhere
                                await update_live_match_home_score(item.matchId, match_score_datails.homeScore)
        
                            if match_score_datails.awayScore != item.awayTeamScore:
                                item.awayTeamScore= match_score_datails.awayScore
                                await update_live_match_away_score(item.matchId, match_score_datails.awayScore)
        
                            # if the home score and away score have been upated I belive we will have to do the changes on the db too
        
                            # no matter what we will alwasy call the match object from db and thus we just call it anyways whether the scores have been updated or not
                            db_match_object= await update_home_score_and_away_score_on_db(
                                db,
                                item.matchId, 
                                match_score_datails.homeScore,
                                match_score_datails.awayScore,
                                FixtureStatus.expired ,
                                determine_winner= True) # we determine the winner since it is set to True
        
                            if db_match_object:
                                await remove_match_from_redis_redis_store(item.matchId)
                                await update_stake_with_winner_data_and_do_payouts(
                                    db, 
                                    item.matchId, 
                                    db_match_object.winner)


                except Exception as match_error:
                    logger.error(f"Error processing match {item.matchId}: {str(match_error)}", exc_info=True)
                    continue  # Continue with next match


        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"an error occured while trying to handle matches iteration, {str(e)}",
            exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to handle matches iteration, {str(e)}"
        )                    

liveDataBackup= LiveDataServiceBackup()