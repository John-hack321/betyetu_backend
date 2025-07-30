from aiohttp import http_exceptions
from fastapi import HTTPException , status

import httpx
import os
import logging
import aiohttp

from dotenv import load_dotenv

from pydantic_schemas.chess_player_schemas import CreateChessDbProfile, country_code

logger = logging.getLogger(__name__)
load_dotenv()

class ChessPlayerService:
    def __init__(self , username : str):
        self.username = username
        self.base_url = os.getenv('CHESS_BASE_URL')

    async def parse_chess_url(self , endpoint : str):
        """
        this if for parsing the url to the different endpoints 
        it does an addition of the endpoint we are targeting to the base url
        """
        try : 
            url_embedded_endpoint = self.base_url + endpoint
            return url_embedded_endpoint
        except Exception as e : 
            logger.error(f'failed to parse the url to the desired standard {e}')
            raise RuntimeError(f'the was an error parsing the url ')

    async def parse_chess_response_data(self, chess_data: dict) -> CreateChessDbProfile:
        """
        Extract the relevant data we want from the response
        Parse the country variable to the desired enum type
        Return the parsed response to the user
        """
        try:
            # First, parse the country code
            country_url = chess_data.get('country', '')
            parsed_country = 254  # Default to Kenya
            
            if country_url:
                try:
                    country_code_str = country_url.rstrip('/').split('/')[-1].upper()
                    if hasattr(country_code, country_code_str):
                        parsed_country = getattr(country_code, country_code_str)
                except Exception as e:
                    logger.error(f'Error parsing country code: {e}')
            
            # Get account status (default to 1 for 'basic')
            status_str = chess_data.get('status', 'basic').lower()
            account_status = 1  # Default to basic
            if hasattr(account_status_code, status_str):
                account_status = getattr(account_status_code, status_str)
            
            # Create and return the profile with proper enum values
            return CreateChessDbProfile(
                user_id=0,  # This will be set by the calling function
                chess_username=chess_data.get('username', ''),
                player_id=chess_data.get('player_id', 0),
                followers=chess_data.get('followers', 0),
                country=parsed_country,
                account_status=account_status,
                account_verification_status=chess_data.get('verified', False),
                league=chess_data.get('league', 'wood')
            )

        except Exception as e:
            print(f'ther was na error parsing the repsonse data => detail : {str(e)}')
            raise RuntimeError('the parse_chess_response_data_funcion failed')

    async def fetch_user_profile_data(self):
        """
        functoin for fetching the actual player data from chess.com
        set the endpoint to be the username of the chess player for chess.com
        create a session for a get request to fetch user data from chess.com
        parse the chess response data to desired format based on the application 
        return the parsed response to the application
        """
        try : 
            endpoint = self.username
            url = await self.parse_chess_url(endpoint)
            # do an api call to the chess.com servers with url returned
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        print(f'fetch was successful : {response_data}')
                        # we will now parse the response to the format expected by the application
                        parsed_response = await self.parse_chess_response_data(response_data)
                        return parsed_response
                    else : 
                        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "the chess.com data fetch was unsuccessful with response code : {response.status}")

        except Exception as e: 
            logger.error(f'failed to fetch user data {e}')
            raise RuntimeError(f'the fetch user data function failed')