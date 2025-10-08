from dotenv import load_dotenv
import os
import aiohttp

from fastapi import HTTPException , status
from requests import status_codes
from sqlalchemy import true
from sqlalchemy.orm import query

from api.amin_routes.util_leagues import add_league_to_db

class FootballDataService():
    def __init__(self):
        self.football_data_api_key= os.getenv('FOOTBALL_API_KEY')
        self.football_data_api_url= os.getenv('FOOTBALL_API_URL')

    # FOOTBALL API UTILITY FUNCTIONS #
    # league utility functions 
    async def parse_league_data(self ,data):
        leagues_list_object = data.get('response').get('leagues')
        return leagues_list_object

    async def add_leagues_to_database(leagues_list_object):
        """
        we will have to iterate through the list in order to add the data to the database
        """
        for item in leagues_list_object:
            db_league = await add_league_to_db(item)
            if not db_league:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
                detail=f"unable to add league of id {item.get('id')} and name : {item.get('username')} to the database")

    # fixture utility functions
    async def validate_outcome(home : str, away : str, home_score : str, away_score : str, is_played : bool):
        if is_played :
            if home_score > away_score :
                return home
            elif away_score > home_score:
                return away
            else :
                return "draw"

        else :
            return null


    async def parse_fixtures_data(match_object_list):
        parsed_match_object_list= []
        for item in match_object_list:
            match_id= item.get('id')
            home_team_id= item.get('home').get('id')
            home_team= item.get('home').get('name')
            away_team_id= item.get('away').get('id')
            away_team= item.get('away').get('name')
            match_date= item.get('status').get('utcTime')
            home_score= item.get('home').get('score')
            away_score= item.get('away').get('score')
            is_played= item.get('status').get('started')
            
            outcome = validate_outcome(home_team, away_team, home_score, away_score, is_played)

            match_dict = {
                'match_id' : match_id,
                'home_team_id' : home_team_id,
                'home_team' : home_team,
                'away_team_id' : away_team_id,
                'away_team' : away_team,
                'match_date' : match_date,
                'home_score' : home_score,
                'away_score' : away_score,
                'is_played' : is_played,
                'outcome' : outcome,
            }

            parsed_match_object_list.append(match_dict)

        return parsed_match_object_list

    async def add_parsed_matches_object_to_database(matches_object_list):
        """
        we will use a loop to add the data to the database
        """
        for item in matches_object_list:
            try :
                db_object = add_match_to_db(item)
            except Exception as e:
                raise RuntimeError(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
                detail = "failed to add match to the database")

    # general utility functions    
    async def make_get_api_call(self, api_url : str , headers : dict , params : str = None):
        async with aiohttp.ClientSession() as session:
            if query_string :
                async with session.get(api_url, headers, params) as response:
                    response_data = await response.json()
                    return response_data
            async with session.get(api_url , headers=headers) as response:
                response_data = await response.json()
                return response_data


    # FOOTBALL API ACTUAL FUNCTIONS #

    async def add_leagues(self):
        try :
            headers = {
            "x-rapidapi-key": self.football_data_api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
            }

            try:
                response_data = await make_get_api_call(self.football_data_api_url, headers)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
                detail="failed to make the api call to fetch leagues : {e}")

            extracted_leagues_list = await parse_league_data(response_data)

            try :
                await add_leagues_to_database(extracted_leagues_list)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
                detail="failed to add leagues to the databse : {e}")

            return True

        except Exception as e:
            raise RuntimeError(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
            detail="the add leagues service failed : {e}")

    async def add_fixutures_by_league_id(self ,league_id):
        """
        Adds the fixtures to the database according to the league id
        """
        headers = {
            "x-rapidapi-key": self.football_data_api_key,
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
        }

        query_string={"leagueid": league_id}

        response_data = make_get_api_call(self.football_data_api_url, headers, query_string)

        parsed_match_list_data = await parsed_match_list_data(response_data)