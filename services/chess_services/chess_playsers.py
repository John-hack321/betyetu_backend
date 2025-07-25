from fastapi import HTTPException , status

import httpx
import os
import logging

from dotenv import load_dotenv

from fast_api.pydantic_schemas.chess_player_schemas import country_code

logger = logging.getLogger(__name__)
load_dotenv()

class ChessPlayerService:
    def __init__(self , username : str):
        self.username = username
        self.base_url = os.get('CHESS_BASE_URL')

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

    async def parse_chess_response_data(self ,chess_data : dict):
        """
        extract the relevant data we want form the response
        we then parse the coutry variable to a the desired enum type
        return the parsed response to the user
        """
        try :
            chess_data = {
            'chess_username' : chess_data.get('username'),
            'player_id' : chess_data.get('player_id'),
            'followers' : chess_data.get('followers'),
            'country' : chess_data.get('country'),
            'account_status' : chess_data.get('status'),
            'chess_account_verification_status' : chess_data.get('verified'),
            'league' : chess_data.get('league'),
            }
            # we need logic for parsing the courtry response here
            async def parse_country_var(country_url : str):
                try :
                    country_code_string = country_url.rstrip('/').split('/')[-1].upper() # this gets the last value after deviding the values using the slashes in the url 
                    # at this point we now have the country code that is KE in strin format but we now need a way to get in an enum func way :
                    mapped_country_code_string = country_code[country_code_string.upper()] # this gives us country_code.KE
                    return mapped_country_code_string # returning this is the same as returning country_code.KE
                except Exception as e:
                    logger.error(f'the parse country function run into an error : {e}')
                    raise RuntimeError(f'the parse_country_var function failed')
            chess_data['country'] = parse_country_var(chess_data['country'])
            return chess_data

        except Exception as e:
            print(f'ther was na error parsing the repsonse data => detail : {str(e)}')
            raise RuntimeError('the parse_chess_response_data_funcion failed')

    async def fetch_user_data_on_signup(self):
        try : 
            endpoint = self.username
            url = await self.parse_chess_url(endpoint)
            # do an api call to the chess.com servers with url returned
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f'the response was successful {response.json()}')
                    response = response.json() # we have to convert this to json format to make it better
                    # we now parse the json data here before returning
                    parsed_response = await self.parse_chess_response_data(response_data)
                    return parsed_response
                else : 
                    raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "there was an error of status code {response.status} fetching the user data from chess.com ")
        
        except Exception as e: 
            logger.error(f'failed to fetch user data {e}')
            raise RuntimeError(f'the fetch user data function failed')