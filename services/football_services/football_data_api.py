from datetime import datetime
from urllib import response
from dotenv import load_dotenv
import os
import aiohttp
import logging

from fastapi import HTTPException , status
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_routes.util_leagues import add_league_to_db
from api.admin_routes.util_matches import add_match_to_db
from pydantic_schemas.fixtures_schemas import MatchObject
from api.admin_routes.util_leagues import get_leagues_list_from_db
from db.models.model_fixtures import FixtureStatus
from db.models.model_leagues import League
from pydantic_schemas.league_schemas import LeagueBaseModel
from sqlalchemy.future import select
from typing import List, Dict, Any

load_dotenv()

logger= logging.getLogger(__name__)

class FootballDataService():
    def __init__(self):
        self.football_data_api_key = os.getenv('FOOTBALL_API_KEY')
        self.football_match_by_league_url = os.getenv('FOOTBALL_API_MATCHES_BY_LEAGUE_URL')
        self.football_all_leagues_url = os.getenv('FOOTBALL_API_ALL_LEAGUES_URL')
        self.solo_league_api_url = os.getenv('SOLO_LEAGUE_API_URL')
        self.popular_leagues_url = "https://free-api-live-football-data.p.rapidapi.com/football-popular-leagues"

    # FOOTBALL API UTILITY FUNCTIONS #
    # league utility functions 
    async def parse_league_data(self ,data):
        leagues_list_object = data.get('response').get('leagues')
        return leagues_list_object

    async def add_leagues_to_database(self, db: AsyncSession, leagues_list_object):
        """
        Iterate through the list and add each league to the database
        """
        from pydantic_schemas.league_schemas import LeagueBaseModel
        
        for item in leagues_list_object:
            # Convert the dictionary to a LeagueBaseModel
            league_data = LeagueBaseModel(
                id=item.get('id'),
                name=item.get('name'),
                localized_name=item.get('name'),  # Using name as localized_name if not provided
                logo_url=item.get('logo', ''),  # Default empty string if logo not provided
                fixture_added=False # once fixture is added this is made to true and the league is also added to popular leageu
            )
            
            db_league = await add_league_to_db(db, league_data)
            if not db_league:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unable to add league with id {item.get('id')} and name: {item.get('name')} to the database"
                )

    async def __parse_solo_league_object(self, response_data):

        try:
            id= response_data.get("response").get("leagues").get("id")
            name= response_data.get("response").get("leagues").get("shortName")
            localized_name= response_data.get("response").get("leagues").get("shortName")
            logo_url= ""
            fixture_added= False

            return {
                "id": id,
                "name": name,
                "localized_name": localized_name,
                "logo_url": logo_url,
                "fixture_added": fixture_added,
            }


        except Exception as e:
            logger.error(f"an error occured while parsing solo league object: {str(e)}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occured while parsing the solo leageu object: {str(e)}"
            )

    # fixture utility functions
    async def validate_outcome(self ,home : str, away : str, home_score : str, away_score : str, is_played : bool):
        if is_played :
            if home_score > away_score :
                return home
            elif away_score > home_score:
                return away
            else :
                return "draw"
        else :
            return None

    async def parse_fixtures_data(self, match_object_response , league_id):
        parsed_match_object_list= []
        match_object_list = match_object_response['response']['matches']
        for item in match_object_list:
            match_id= item.get('id')
            home_team_id= item.get('home').get('id')
            home_team= item.get('home').get('name')
            away_team_id= item.get('away').get('id')
            away_team= item.get('away').get('name')
            # Convert UTC time string to timezone-naive datetime
            match_date_str = item.get('status', {}).get('utcTime')
            match_date = None
            if match_date_str:
                if match_date_str.endswith('Z'):
                    match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    # Convert to timezone-naive datetime
                    match_date = match_date.replace(tzinfo=None)
                else:
                    match_date = datetime.fromisoformat(match_date_str)
                    # Ensure it's timezone-naive
                    if match_date.tzinfo is not None:
                        match_date = match_date.replace(tzinfo=None)
            home_score= item.get('home').get('score')
            away_score= item.get('away').get('score')
            is_played= item.get('status').get('finished')

            # handle marking of whether the match is played or not
            fixture_status= FixtureStatus.future
            if is_played == True:
                fixture_status= FixtureStatus.expired

            league_id= league_id
            
            outcome = await self.validate_outcome(home_team, away_team, home_score, away_score, is_played)
            
            match_dict = {
                'match_id' : int(match_id),
                'home_team_id' : int(home_team_id),
                'home_team' : home_team,
                'away_team_id' : int(away_team_id),
                'away_team' : away_team,
                'match_date' : match_date,
                'home_score' : home_score,
                'away_score' : away_score,
                'is_played' : is_played,
                'outcome' : outcome,
                'league_id' : league_id,
                'fixture_status': fixture_status,
            }

            # appranetly in pydantic version 2 you have to use the model_validate when passing a dictionary to a pydantic basemodel
            match_dict = MatchObject.model_validate(match_dict)

            parsed_match_object_list.append(match_dict)

        return parsed_match_object_list

    async def add_parsed_matches_object_to_database(self,db : AsyncSession, matches_object_list : MatchObject):
        """
        we will use a loop to add the data to the database
        """
        for item in matches_object_list:
            try :
                db_object = await add_match_to_db(db ,item)
                print(f'mathc with match_id of {db_object.match_id} as been added to the database successfuly')
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
                detail = f"failed to add match to the database, with error : {e}")

    # general utility functions    
    async def make_get_api_call(self, api_url: str, headers: dict, params: dict = None):
        async with aiohttp.ClientSession() as session:
            try:
                if params:
                    async with session.get(api_url, headers=headers, params=params) as response:
                        response.raise_for_status()
                        response_data = await response.json()
                        logger.info(f'API call successful: {response.status}')
                        return response_data
                else:
                    async with session.get(api_url, headers=headers) as response:
                        response.raise_for_status()
                        response_data = await response.json()
                        logger.info(f'API call successful: {response.status}')
                        return response_data
            except aiohttp.ClientError as e:
                logger.error(f'API call failed: {str(e)}')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f'Failed to make API request: {str(e)}'
                )


    # FOOTBALL API ACTUAL FUNCTIONS #

    #for leageu not in the general leageu fetching
    async def add_league_data_by_league_id(self, league_id: int, db: AsyncSession):
        try:

            headers = {
                'x-rapidapi-key': "acb3433c53msh05ecefe0d28a671p13e83fjsn1e3195a130d9",
                'x-rapidapi-host': "free-api-live-football-data.p.rapidapi.com"
            }

            api_response= await self.make_get_api_call(f"{self.solo_league_api_url}{league_id}",
            headers=headers,
            params= None)

            parsed_solo_league_response=await self.__parse_solo_league_object(api_response)

            league_data= LeagueBaseModel(**parsed_solo_league_response)
            db_league_object= await add_league_to_db(db, league_data)
            if not db_league_object:
                logger.error(f"object returned from db is not as expected: __add_league_data_by_league_id")


        except Exception as e:
            logger.error(f"an error occured while adding leageu by league id to the database, {str(e)}",
            exc_info=True)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occured whle adding leageu data by id to system: {str(e)}"
            )

    async def fetch_popular_leagues(self) -> List[Dict[str, Any]]:
        """Fetch the list of popular leagues from the API"""
        try:
            headers = {
                'x-rapidapi-key': self.football_data_api_key,
                'x-rapidapi-host': "free-api-live-football-data.p.rapidapi.com"
            }

            response = await self.make_get_api_call(
                self.popular_leagues_url,
                headers=headers,
                params=None
            )

            if response and response.get('status') == 'success':
                return response.get('response', {}).get('popular', [])
            return []

        except Exception as e:
            logger.error(f"Error fetching popular leagues: {str(e)}", exc_info=True)
            return []

    async def add_popular_leagues(self, db: AsyncSession) -> bool:
        """Fetch popular leagues and add them to the database if they don't exist"""
        try:
            popular_leagues = await self.fetch_popular_leagues()
            if not popular_leagues:
                logger.warning("No popular leagues found in the API response")
                return False

            added_count = 0
            for league in popular_leagues:
                # Check if league already exists
                existing_league = await db.execute(
                    select(League).where(League.id == league.get('id'))
                )
                existing_league = existing_league.scalar_one_or_none()

                if not existing_league:
                    # Create league data matching your LeagueBaseModel
                    league_data = {
                        "id": league.get('id'),
                        "name": league.get('name'),
                        "localized_name": league.get('localizedName', league.get('name')),
                        "logo_url": league.get('logo', ''),
                        "fixture_added": False
                    }
                    
                    # Add league to database
                    db_league = League(**league_data)
                    db.add(db_league)
                    added_count += 1

            if added_count > 0:
                await db.commit()
                logger.info(f"Successfully added {added_count} popular leagues to the database")
            else:
                logger.info("No new popular leagues to add")

            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding popular leagues: {str(e)}", exc_info=True)
            return False

    async def add_leagues(self, db: AsyncSession):
        """
        get a list of all leagues available in the api and adds them to the database
        """
        try :
            headers = {
            "x-rapidapi-key": self.football_data_api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
            }

            try:
                response_data = await self.make_get_api_call(self.football_all_leagues_url, headers)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
                detail=f"failed to make the api call to fetch leagues , with error : {e}")

            extracted_leagues_list = await self.parse_league_data(response_data)

            try :
                await self.add_leagues_to_database(db ,extracted_leagues_list)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
                detail=f"failed to add leagues to the databse : error message {e}")

            return True

        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
            detail=f"the add leagues service failed : error message :  {e}")

    async def add_fixutures_by_league_id(self, db: AsyncSession, league_id: int):
        """
        Adds the fixtures to the database according to the league id
        """
        try:
            # First, check if the league exists in the database
            existing_league = await db.execute(
                select(League).where(League.id == league_id)
            )
            existing_league = existing_league.scalar_one_or_none()

            # If the league doesn't exist, add it first
            if not existing_league:
                logger.info(f"League with ID {league_id} not found in database. Attempting to add it...")
                await self.add_league_data_by_league_id(league_id, db)
                logger.info(f"Successfully added league with ID {league_id} to the database")

            headers = {
                "x-rapidapi-key": self.football_data_api_key,
                "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
            }

            query_string = {"leagueid": league_id}
            response_data = await self.make_get_api_call(self.football_match_by_league_url, headers, query_string)
            parsed_match_list_data = await self.parse_fixtures_data(response_data, league_id)

            try:
                await self.add_parsed_matches_object_to_database(db, parsed_match_list_data)
                logger.info(f"Successfully added fixtures for league ID {league_id}")
                return True
            except Exception as e:
                logger.error(f'Failed to add fixtures to database: {str(e)}', exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to add fixtures to database: {str(e)}"
                )

        except HTTPException:
            # Re-raise HTTP exceptions as they are
            raise
        except Exception as e:
            logger.error(f'Unexpected error in add_fixutures_by_league_id: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}"
            )

    """
    this will be used for fetching match scores based ont he match id
    it is mostly defined for the sake of helping out in the live data service when processing matches that have ended
    """
    async def get_match_scores_by_match_id(self, match_id: int):
        pass


football_data_api_service= FootballDataService()