# the way to go for this api is to use aiohttp library from python as it is fastapi compatible and all 

import asyncio
import aiohttp
from aiohttp import http_exceptions
from fastapi import HTTPException , status
import logging
import enum

from enum import Enum

class EndpointType(Enum):
    PROFILE = ''
    GAMES = '/games'
    STATS = '/stats'
    TO_MOVE = '/to-move'
    ARCHIVES = '/archives'
    CLUB = '/clubs'


logger = logging.getLogger(__name__)

class ChessPlayerService:
    def __init__(self , username : str):
        self.username = username

    async def parse_chess_url(self ,endpoint : str):
        # for multipurpose usage you might wanna make this usable by all endpoints
        base_url = 'https://api.chess.com/pub/player/'
        endpoint_url = base_url + endpoint
        return endpoint_url

    # andpoint for fetching player profile data
    async def fetch_user_data(self , url_endpoint : str):
       try :
            headers = {
                "User-Agent": "Mozilla/5.0 (OnlineTournamentScheduler/1.0)" # moxilla mimics real browser action and the chess name ther is a custom name for our app
                }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url_endpoint) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        # print(response_data)
                        return response_data
                    else :
                        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'the user profile data request failed')

       except Exception as e :
            logger.error(f'the fetch user data function failed : {e}')
            raise RuntimeError('there was an error fetching user data')
    
    # endpoint for fetching player games data
    async def fetch_player_games_data(self):
        endpoint = 'hikaru/games'
        headers = {
            "User-Agent": "Mozilla/5.0 (OnlineTournamentScheduler/1.0)"
        }
        try :
            parsed_url = await self.parse_chess_url(endpoint)
            async with aiohttp.ClientSession(headers = headers) as session:
                async with session.get(parsed_url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data
                    else :
                        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = f"failed fetch of error code : {response.status}")
        except Exception as e :
            logger.error(f'an error occured while fetching player user data ')
            raise RuntimeError(f'the fetch player user data funtion failed')

    async def general_url_parser(self ,username : str , endpoint : str):
        base_url = 'https://api.chess.com/pub/player/'
        endpoint_url = base_url + username + endpoint
        return endpoint_url

    async def general_purpose_endpoint(self , username : str , endpoint : EndpointType ):
        endpoint_str = endpoint.value
        parsed_url = await self.general_url_parser(username , endpoint_str)
        headers = {
            "User-Agent" : "Mozilla/5.0 (OnlineTournamentScheduler/1.0)"
        }
        try :
            async with aiohttp.ClientSession(headers = headers) as session:
                async with session.get(parsed_url) as response:
                    if response.status == 200 :
                        print(f'response was successful status_coe : {response.status}')
                        response_data = await response.json()
                        return response_data
        except Exception as e :
            logger.error(f'the was an error fetching user data : {str(e)}')
            raise RuntimeError(f'the general purpose fetch function failed')

    async def fetch_data(self): # dont always miss the self paramter in your functions okay 
        # lets put a list for holding up all of this data 
        chess_player_data = []
        
        try :
            """
            parsed_url = await self.parse_chess_url(self.username)
            user_chess_profile_data = await self.fetch_user_data(parsed_url)
            # save profiled data to list after fetching
            chess_player_data.append(user_chess_profile_data)
            # now fetching chess game data
            chess_player_game_data = await self.fetch_player_games_data()
            chess_player_data.append(chess_player_game_data)
            # we finally print the data at the end of it all 
            print(chess_player_data)
            """
            player_profile_data = await self.general_purpose_endpoint(self.username , EndpointType.PROFILE)
            player_game_data = await self.general_purpose_endpoint(self.username , EndpointType.GAMES)
            player_stats = await self.general_purpose_endpoint(self.username , EndpointType.STATS)
            player_archive = await self.general_purpose_endpoint(self.username , EndpointType.ARCHIVES)
            player_to_move = await self.general_purpose_endpoint(self.username , EndpointType.TO_MOVE)
            player_clubs = await self.general_purpose_endpoint(self.username , EndpointType.CLUB)

            return {'player_profile' : player_profile_data ,
             'player_game_data' : player_game_data ,
              'player_stats' : player_stats, 
              'archives' : player_archive ,
              'player_to_move' : player_to_move ,
              'player_clubs' : player_clubs}

        except Exception as e :
            logger.error(f'failed to the requests to chess.com {e}')
            raise RuntimeError(f'the fech data function failed')
        

async def main():
    test_object = ChessPlayerService('JohnKingChessLord')
    output = await test_object.fetch_data()
    print(output)

asyncio.run(main())