from fastapi import HTTPException, status

import aiohttp
import os
import logging
from dotenv import load_dotenv

from pydantic_schemas.chess_player_schemas import country_code
from pydantic_schemas.chess_player_schemas import account_status_code

logger = logging.getLogger(__name__)
load_dotenv()


class ChessPlayerService:
    def __init__(self, username: str):
        self.username = username
        self.base_url = os.getenv('CHESS_BASE_URL')

    async def parse_chess_url(self, endpoint: str):
        """
        this is for parsing the url to the different endpoints 
        it does an addition of the endpoint we are targeting to the base url
        """
        try:
            url_embedded_endpoint = self.base_url + endpoint
            return url_embedded_endpoint
        except Exception as e:
            logger.error(f'failed to parse the url to the desired standard {e}')
            raise RuntimeError(f'there was an error parsing the url')

    async def parse_chess_response_data(self, chess_data: dict):
        """
        extract the relevant data we want from the response
        we then parse the country variable to the desired enum type
        return the parsed response to the user
        """
        try:
            parsed_data = {
                'chess_username': chess_data.get('username'),
                'player_id': chess_data.get('player_id'),
                'followers': chess_data.get('followers'),
                'country': chess_data.get('country'),
                'account_status': chess_data.get('status'),
                'account_verification_status': chess_data.get('verified'),
                'league': chess_data.get('league'),
            } 

            # i belive we need another function for parsing the account status enum too
            async def parse_account_status(status : str):
                try :
                    mapped_account_status = account_status_code[status]
                    return mapped_account_status
                except Exception as e :
                    looger.error(f'an error occured while trying to parse the account status enum : {str(e)}')
                    raise RuntimeError(f'the parse account status function failed')
            
            # we need logic for parsing the country response here
            async def parse_country_var(country_url: str):
                try:
                    country_code_string = country_url.rstrip('/').split('/')[-1].upper()
                    # at this point we now have the country code that is KE in string format
                    mapped_country_code = country_code[country_code_string] # this now returns the desired enum type we want
                    return mapped_country_code
                except Exception as e:
                    logger.error(f'the parse country function run into an error: {e}')
                    return country_code.KE  # Default fallback to Kenya
            """
            when parsing the courtry var we will first check to see if it exists 
            if it exits then we will parse to the desired enum format
            if does not exist we will default to the KE enum code 254
            """
            if parsed_data.get('country'):
                parsed_data['country'] = await parse_country_var(parsed_data.get('country'))
            else:
                parsed_data.get['country'] = country_code.KE  # Default fallback to Kenya
            
            # after parsing the courtry variable of the json object we will now parse the account status to the required version too
            if parsed_data.get('account_status') :
                parsed_data['account_status'] = await parse_account_status(parsed_data.get('account_status'))
            else :
                parsed_data['account_status'] = account_status_code.basic # default to the basic one 

            
            # for debuggin purposes i will print the parsed data in order to see its sctructure to ensure we have  a solid json structure            
            print(f'parsing of the data from chess.com was successful as seen : {parsed_data}')
            return parsed_data

        except Exception as e:
            logger.error(f'there was an error parsing the response data => detail: {str(e)}')
            raise RuntimeError('the parse_chess_response_data_function failed')

    async def fetch_user_profile_data(self):
        try:
            endpoint = self.username
            url = await self.parse_chess_url(endpoint)
            # do an api call to the chess.com servers with url returned
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        print(f'the response was successful {response_data}')
                        # we now parse the json data here before returning
                        parsed_response = await self.parse_chess_response_data(response_data)
                        return parsed_response
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"there was an error of status code {response.status} fetching the user data from chess.com"
                        )
        
        except Exception as e:
            logger.error(f'failed to fetch user data {e}')
            raise RuntimeError(f'the fetch user data function failed')