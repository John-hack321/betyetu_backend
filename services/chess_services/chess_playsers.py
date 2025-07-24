from fastapi import HTTPException , status

import asyncio
import httpx
import aiohttp
import requests
import os
import logging

from dotenv import load_dotenv
from urllib3.util import parse_url

from fast_api.api.utils.util_chess_players import add_new_chess_player

logger = logging.getLogger(__name__)
load_dotenv()

class ChessPlayerService:
    def __init__(self , username : str):
        self.username = username
        self.base_url = os.get('CHESS_BASE_URL')

    async def parse_url(self , endpoint : str):
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

    async def parse_chess_response_data(chess_data : dict):
        """
        extract the relevant data we want form the response
        we then parse the coutry one since the api returns it in form of a url
        return the parsed response to the user
        """
        try :
            chess_data = {
            'chess_username' : data.get('username'),
            'player_id' : data.get('player_id'),
            'followers' : data.get('followers'),
            'country' : data.get('country'),
            'account_status' : data.get('status'),
            'account_verification_status' : data.get('verified'),
            'league' : data.get('league'),
            }
            # we need logic for parsing the courtry response here
            async def parse_country_var():
                ...
            chess_data['country'] = parse_country_var(chess_data['country'])

            return chess_data
        
        except Exception as e:
            print(f'ther was na error parsing the repsonse data => detail : {str(e)}')
            raise RuntimeError('the parse_chess_response_data_funcion failed')

    async def fetch_user_data_on_signup(self):
        try : 
            endpoint = self.username
            url = parse_url(endpoint)
            # do an api call to the chess.com servers with url returned
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status == 200:
                    print(f'the response was successful {response.json()}')
                    response = response.json() # we have to convert this to json format to make it better
                    # we now parse the json data here before returning
                    parsed_response = await parse_chess_response_data(response)
                    return await parsed_response
                else : 
                    raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "there was an error of status code {response.status} fetching the user data from chess.com ")
        
        except Exception as e: 
            logger.error(f'failed to fetch user data {e}')
            raise RuntimeError(f'the fetch user data function failed')

