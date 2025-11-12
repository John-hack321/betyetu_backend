import aiohttp
from fastapi  import status , HTTPException
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

# the first step is to get the access token for validation

MPESA_ACCESS_TOKEN_URL = os.getenv('MPESA_ACCESS_TOKEN_URL')
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_SHORT_CODE = os.getenv('MPESA_SHORT_CODE')
MPESA_CALL_BACK_URL = os.getenv('MPESA_CALL_BACK_URL')
MPESA_PASS_KEY = os.getenv('MPESA_PASS_KEY')

import logging

logger= logging.getLogger(__name__)

# lets wrap all of thise function into logic for ease of use right ?
# lest first create a function for checking if the token is expired if it is then it generate a new one 

class MpesaTokenManager: # This will assist in the management of our token so that we dont send expired tokens 
    def __init__(self , cache_file='token.json'):
        self.consumer_key = MPESA_CONSUMER_KEY
        self.consumer_secret = MPESA_CONSUMER_SECRET
        self.token_url = MPESA_ACCESS_TOKEN_URL
        self.cache_file = cache_file

    def get_token(self):
        token = self._read_cached_token()
        if token:
            return token
        return self._generate_new_token()

    def _read_cached_token(self):
        try:
            with open(self.cache_file , 'r') as f:
                data = json.load(f)
                if time.time() < data['expires_at']:
                    return data['access_token']
        except (FileNotFoundError , json.JSONDecodeError):
            pass
        return None
    
    def _generate_new_token(self):
        try : 
            auth = (self.consumer_key , self.consumer_secret)
            response = requests.get(self.token_url , auth = auth )
            if response.status_code == 200:
                access_token = response.json()['access_token']
                expires_at = time.time() + 3600 - 60
                self._cache_token(access_token , expires_at)
                return access_token
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = f'failed to get the access token : {response.text}')
            
        except Exception as e :
            logger.error(f'failed to generate a new token : {e}')
            raise RuntimeError(f'the generate new_token_function failed')
            
    def _cache_token(self, token , expires_at):
        data = {
            'access_token' : token,
            'expires_at' : expires_at,
        }
        with open(self.cache_file , 'w') as f:
            json.dump(data , f)

async def create_stk_push( MPESA_PASS_KEY : str , MPESA_STK_URL : str , phone : str , amount : str):
    """
    check if token is expired with the mpesa token manager
    generate the password / passkey for the payload auth
    generate the payload using passed in data , the passcode and some env variables
    create the headers for the request 
    generate the request in async fasion for performance
    """
    try :
        token_istance = MpesaTokenManager()
        present_token = token_istance.get_token()
        access_token = present_token
        # by this point the programm will have checked for the access token and if not present it will generate a new one 
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode((MPESA_SHORT_CODE + MPESA_PASS_KEY + timestamp).encode()).decode()
        # construct the payload : 
        payload = {
        "BusinessShortCode": MPESA_SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORT_CODE, # is a constant
        "PhoneNumber": phone, 
        "CallBackURL": MPESA_CALL_BACK_URL,
        "AccountReference": "cod_wars", # this will soon be a constant i think 
        "TransactionDesc": "test_deposit" # a constant since all stk pusheds will be deposits i think 
    }
        # initilaize some headers for the request itself 
        headers = { # this is constant accross all requests 
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'}

        try :
            async with aiohttp.ClientSession() as session:
                async with session.post(MPESA_STK_URL , json=payload , headers=headers) as response:
                    if response.status == 200:
                        print('the response was successful')
                        response_data = await response.json()
                        return response_data
                    else :
                        print(f'the request was not successful with status code : {response.status}')
        except Exception as e :
            logger.error(f'the request failed : {e}')
            raise RuntimeError(f'the mpesa stk push request failed')

    except Exception as e :
        logger.error(f'the create stk push function failed {e}')
        raise RuntimeError('the create stk push function failed teribly')