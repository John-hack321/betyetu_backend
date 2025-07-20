import fastapi
from fastapi import APIRouter, HTTPException  , status
import os

from api.utils.dependancies import db_dependancy , user_depencancy
from api.utils.util_transactions import add_transaction , create_transaction, create_withdrawal_transaction, get_transaction_and_account_data , update_transaction 
from api.utils.util_users import get_user_and_account_data
from db.models.model_users import Transaction
from pydantic_schemas.transaction_schemas import CreateTransaction, trans_status, trans_type
from api.utils.util_accounts import increment_account_balance, update_account
from api.utils.dependancies import db_dependancy
from services.mpesa_services.mpesa_stk_push import  create_stk_push
from services.mpesa_services.mpesa_b2c_push import B2CPaymentService

from dotenv import load_dotenv

router = APIRouter(
    prefix = "/transactions", 
    tags = ['transaction']
)

load_dotenv()
MPESA_PASS_KEY = os.getenv('MPESA_PASS_KEY')
MPESA_STK_URL = os.getenv('MPESA_STK_URL')

@router.post("/deposit" , status_code = 200)
async def deposit_money(db : db_dependancy , user : user_depencancy , user_transaction_request_data : CreateTransaction):
    user_id = user['user_id']
    user_and_account_data = await get_user_and_account_data(db , user_id)
    # we first have to do the stk push to the user to initiate the transaction so that we record what we are sure of inot the database
    # we put it here so that we can utilize the user data from the database from the databae
    test_phone = '254708374149'
    mpesa_response = await create_stk_push(MPESA_PASS_KEY , MPESA_STK_URL ,test_phone, user_transaction_request_data.amount)
    print(mpesa_response.json())
    mpesa_response = mpesa_response.json()
    # we will check the response code if it is 0 we will create the transaction if not we will raise http error exception 
    if mpesa_response['ResponseCode'] == '0' :
        db_new_transaction = await create_transaction(db , user_transaction_request_data , user_id , user_and_account_data.account.id , 1 , mpesa_response['MerchantRequestID'] , mpesa_response['CheckoutRequestID'] )
        if not db_new_transaction:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to create the new transaction on stk push")
        return {'check_out_id' : db_new_transaction.merchant_checkout_id}
    else :
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'mpesa return error string code instead of 0')

@router.get('/callback')
async def call_back_response( db : db_dependancy , mpesa_call_back_response):
    data = await mpesa_call_back_response.json()
    stk_data = data['Body']['stkCallBack']
    merchant_request_id = stk_data['MerchantRequestID']
    checkout_request_id = stk_data['CheckoutRequestID']
    # extraction of recipt number from the request body
    metadata = stk_data.get('CallbackMetadata' , {}).get('item' , [])
    receipt_number = next( # these to thingies here are carefull extraction of the recipt by carefuly traversing the json object
      (item['value'] for item in metadata if item['name'] == 'MpesaReceiptNumber'),
      None
    )
    if stk_data['ResultCode'] == '0':
        success_db_transaction = await update_transaction(db , trans_type.deposit , merchant_request_id , receipt_number)
        if not success_db_transaction:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to update the transaction data")
        updated_account = await increment_account_balance( db , success_db_transaction.account_id , success_db_transaction.amount  )
        if not updated_account:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to update the account data in the database")
        return {'success' : 'ok'}
    else :
        failed_transaction = update_transaction( db , 0 , merchant_request_id , receipt_number = 'N/A' )
        if not failed_transaction:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'failed to put failed transaction into databaes')

# now we will build this another endpoint for checking if transactio went to completion in order to updatet the frontend
@router.get('/check_deposit_status')
async def check_deposit_status(db : db_dependancy , user : user_depencancy , checkout_id : str):
  transaction_and_account_data = await get_transaction_and_account_data(db , checkout_id)
  if transaction_and_account_data.transaction.status == trans_status.successfull:
    return {
      'balance' : transaction_and_account_data.balance
    }
  else : 
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'the check depsit endpoing failed')
  
# endpoints for withdrawal will now go down here : 

@router.post('/withdrawal') # this will be the endpoint initialting the withdrawal request as initiated by the user : 
async def withdrawal_request(db : db_dependancy , user : user_depencancy ,  user_transaction_request_data : CreateTransaction):
  try:
    #query user and account data 
    user_and_account_data = await get_user_and_account_data(db , user.get(user_di))
    if not user_and_account_data:
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to load user and account data from the database")
    # in production env we will use user_and_account_data.phone instead of test_phone
    test_phone = '254708374149' # this is the test phone that we use for the sandbox environemt 
    b2c_instance = B2CPaymentService()
    response = await b2c_instance.send_b2c_request(user_transaction_request_data.amount , test_phone)
    # continue with logic for adding the transaction and more 
    if response.get(ResponseCode) == '0':
      # if the response code is zero then we will create a pending transaction into the database or else we just create a failed one 
      db_transaction = await create_withdrawal_transaction(db , user_transaction_request_data , user_and_account_data.id , user_and_account_data.account.id , trans_status.pending ,response.get(ConversationID) , ):

  except Exception as e:
    logger.error(f'the b2c endpoint failed : {e}')
    raise RuntimeError(f'the endpoint failed')











@router.get('/withdrawal/success') # this will be for successfully transactions
async def successfull_withdrawal(db , db_dependancy):
  ...

@router.get('/withdrawal/failed_withdrawal')
async def failed_withdrawal(db , db_dependancy):
  ...


















"""
# these are the data points to help me build this system well :

# this is the request body for initiating the request for the b to customer transaction 
{    
   "Initiator":"testapi",
   "SecurityCredential":"IAJVUHDGj0yDU3aop/WI9oSPhkW3DVlh7EAt3iRyymTZhljpzCNnI/xFKZNooOf8PUFgjmEOihUnB24adZDOv3Ri0Citk60LgMQnib0gjsoc9WnkHmGYqGtNivWE20jyIDUtEKLlPr3snV4d/H54uwSRVcsATEQPNl5n3+EGgJFIKQzZbhxDaftMnxQNGoIHF9+77tfIFzvhYQen352F4D0SmiqQ91TbVc2Jdfx/wd4HEdTBU7S6ALWfuCCqWICHMqCnpCi+Y/ow2JRjGYHdfgmcY8pP5oyH25uQk1RpWV744aj2UROjDrxTnE7a6tDN6G/dA21MXKaIsWJT/JyyXg==",
   "CommandID":"BusinessPayToBulk",
   "SenderIdentifierType":"4",
   "RecieverIdentifierType":"4",
   "Amount":"239",
   "PartyA":"600979",
   "PartyB":"600000",
   "AccountReference":"353353",
   "Requester":"254708374149",
   "Remarks":"OK",
   "QueueTimeOutURL":"https://mydomain/path/timeout",
   "ResultURL":"https://mydomain/path/result"
}ConversationID

# this is the response body for confriming receipt of the request 
{
    "OriginatorConversationID": "5118-111210482-1",
    "": "AG_20230420_2010759fd5662ef6d054",
    "ResponseCode": "0",
    "ResponseDescription": "Accept the service request successfully."
}


#the response from the call back functoin 
{    
 "Result":
 {  
   "ResultType": "0",    
   "ResultCode":"0",    
   "ResultDesc": "The service request is processed successfully",    
   "OriginatorConversationID":"626f6ddf-ab37-4650-b882-b1de92ec9aa4",    
   "ConversationID":"12345677dfdf89099B3",    
   "TransactionID":"QKA81LK5CY",    
   "ResultParameters":
     {    
       "ResultParameter": 
          [{
           "Key":"DebitAccountBalance",    
           "Value":"{Amount={CurrencyCode=KES, MinimumAmount=618683, BasicAmount=6186.83}}"
          },
          {
          "Key":"Amount",    
           "Value":"190.00"
          },
           {
          "Key":"DebitPartyAffectedAccountBalance",    
           "Value":"Working Account|KES|346568.83|6186.83|340382.00|0.00"
          },
           {
          "Key":"TransCompletedTime",    
           "Value":"20221110110717"
          },
           {
          "Key":"DebitPartyCharges",    
           "Value":""
          },
           {
          "Key":"ReceiverPartyPublicName",    
           "Value":000000– Biller Companty
          },
          {
          "Key":"Currency",    
           "Value":"KES"
          },
          {
           "Key":"InitiatorAccountCurrentBalance",    
           "Value":"{Amount={CurrencyCode=KES, MinimumAmount=618683, BasicAmount=6186.83}}"
          }]
       },
     "ReferenceData":
       {    
        "ReferenceItem":[
           {"Key":"BillReferenceNumber", "Value":"19008"},
           {"Key":"QueueTimeoutURL", "Value":"https://mydomain.com/b2b/businessbuygoods/queue/"}  
         ] 
      }
 }
}

"""