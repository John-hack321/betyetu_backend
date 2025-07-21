from fastapi import APIRouter, HTTPException  , status
import os

from api.utils import transaction_dependancies
from api.utils.dependancies import db_dependancy , user_depencancy
from api.utils.util_transactions import create_transaction, create_withdrawal_transaction, get_transaction_and_account_data , update_transaction , update_b2c_transaction
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
async def deposit_call_back_response( db : db_dependancy , mpesa_call_back_response):
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
        updated_account = await update_account( db , success_db_transaction.account_id , trans_type.deposit , success_db_transaction.amount  )
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
      db_transaction = await create_withdrawal_transaction(db , user_transaction_request_data ,
       user_and_account_data.id ,
       user_and_account_data.account.id , 
       trans_status.pending ,response.get(ConversationID) ,  
       response.get(OriginatorConversationID))
      if not db_transaction:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = " failed to write the transaction into the database ")
    else : 
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "the status code from safaricom was an error status code")

  except Exception as e:
    logger.error(f'the b2c endpoint failed : {e}')
    raise RuntimeError(f'the endpoint failed')

@router.get('/withdrawal/success') # this will be for successfully transactions
async def successfull_withdrawal(db : db_dependancy , successful_respose):
  try:
    successful_respose_data = await successful_respose.json()
    # here there is no need to check the result code or as it obviously shows that the transaction was successful 
    # i guess the  first thing that we will do is to extract the relevant data from the response and use it to update the db well this is the receipt and the ConversatonID
    response_data = await parse_b2c_response_data(successful_respose_data)
    result_description = response_data.get('result_description',{})
    print(f'result_description :  {result_description}')
    receipt = response_data.get('receipt' , {})
    ConversationID = response_data.get('ConversationID' , {}) # we add the empty parenthesis there so that in case of data not found it defaults to an empty dictionary instead of crashing 
    # we will then use the conversatin id to query and update the transaction as successful 
    updated_successful_transaction = await update_b2c_transaction(db ,ConversationID , trans_status.successfull , receipt )
    if not updated_successful_transaction:
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to update the transaction to be succesfull ")
    # for this succsessful transaction we have to update the account table too 
    updated_account = await update_account(db , updated_successful_transaction.account_id , trans_type.withdrawal , updated_successful_transaction.amount )
    if not updated_account:
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to update laoded account table from the database")
  
  except Exception as e:
    logger.error(f'the successful transactoin endpoing failed {e}')
    raise RuntimeError(f'the successfull withdrawal endpoint failed')

@router.get('/withdrawal/failed_withdrawal')
async def failed_withdrawal(db : db_dependancy , failed_response):
  failed_response_data = await failed_response.json()
  try:
    response_data = await parse_b2c_response_data(failed_response)
    result_description = response_data.get('result_description')
    ConversationID = result_data.get('ConversationID')
    # we will now use these two update the failed transaction into the database
    updated_failed_transaction = await update_b2c_transaction(db , ConversationID , trans_status.failed , receipt = None)
    if not updated_failed_transaction:
      raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to update loaded transaction from the database")
    # for the failed withdarawal transaction there is no need to update the account table

  except Exception as e:
    logger.error(f'the failed withdaral endpoing failed withdrawal endpoing failed : {e}')
    raise RuntimeError(f'there was an error on the withdrawal endpoing')

async def parse_b2c_response_data(data : dict):
  """
  this is a utility function that parses the response data and returns usefull part so that we can use 
  first check what transaction it is by looking at the result code if its 0 then its successful
  for successful ones : 
    we first extract the Conversation id 
    we then extract the receipt in a programmatic way for safety
    return the two in form of a dictionary
  for failed ones : 
    we will extract the transaction description , and the ConversationID 
    we then return the two in form of a dictionary 
  """
  # to make this usable for both sides of the result url we will use if statements to sort out btween successful ones and unsuccessful ones 
  if data['Result']['ResultCode'] == '0':
    try:
      ConversationID = data['Result']['ConversationID']
      result_description = data['Result']['ResultDesc']
      # this is a better for extracting these data points in a safe a programmatic way for the best result 
      parameters = data['Result']['ResultParameters']['ResultParameter'] 
      receipt = next(
        (param['Value'] for param in parameters if param['Key'] == 'TransactionReceipt'),
        None # if the value is not found we fall back to None
      )
      return {'ConversationID' : ConversationID , 'receipt' : receipt , 'result_description' : result_description}

    except Exception as e:
      logger.error(f'failed to parse the b2c response data')
      raise RuntimeError(f'there was a problem with the data parsing logic for the result logic on ')

  else :
    result_data = data['Result']
    result_description = result_data.get('ResultDesc')
    ConversationID = result_data.get('ConversationID')
    return {'result_description' : result_description , 'ConversationID' : ConversationID}