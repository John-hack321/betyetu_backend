from datetime import datetime
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

load_dotenv()

logger= logging.getLogger(__name__)

class FootballDataService():
    def __init__(self):
        self.football_data_api_key= os.getenv('FOOTBALL_API_KEY')
        self.football_match_by_league_url= os.getenv('FOOTBALL_API_MATCHES_BY_LEAGUE_URL')
        self.football_all_leagues_url= os.getenv('FOOTBALL_API_ALL_LEAGUES_URL')

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
                fixture_added=False
            )
            
            db_league = await add_league_to_db(db, league_data)
            if not db_league:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unable to add league with id {item.get('id')} and name: {item.get('name')} to the database"
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
            is_played= item.get('status').get('started')
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

    async def add_leagues(self , db : AsyncSession):
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

    async def add_fixutures_by_league_id(self ,db : AsyncSession, league_id):
        """
        Adds the fixtures to the database according to the league id
        """
        headers = {
            "x-rapidapi-key": self.football_data_api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
        }

        query_string={"leagueid": league_id}

        response_data = await self.make_get_api_call(self.football_match_by_league_url, headers, query_string)

        parsed_match_list_data = await self.parse_fixtures_data(response_data, league_id)

        try:
            await self.add_parsed_matches_object_to_database(db, parsed_match_list_data)
            return True
        except Exception as e:
            logger.error(f'an unexpected error occured on the add_parsed_matches_object_to_database {str(e)}', exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
            detail= f"an error occured on on the_add_fixtures_list_object_to_database {str(e)}")

    """
    will be used for getting fixtures by id from the api source
    TODO: fetch fixture by match id
    TODO: proccess the fixture data to a state that we can easily get data points that we want
    """
    async def __fetch_fixture_by_match_id_from_api(self, match_id: int):
        # TODO: define the logic for getting the fixture of one match by league id
        pass


football_data_service= FootballDataService()