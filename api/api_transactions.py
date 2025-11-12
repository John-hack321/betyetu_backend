from aiohttp import http_exceptions
from fastapi import APIRouter, HTTPException  , status , Request
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
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix = "/transactions", 
    tags = ['transactions']
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
    # test_phone = '254724027231'
    mpesa_response_data = await create_stk_push(MPESA_PASS_KEY , MPESA_STK_URL, user_and_account_data.phone, user_transaction_request_data.amount)
    print(mpesa_response_data)
    # we will check the response code if it is 0 we will create the transaction if not we will raise http error exception 
    if mpesa_response_data.get('ResponseCode') == '0' :
        db_new_transaction = await create_transaction(db , user_transaction_request_data , user_id , user_and_account_data.account.id , trans_status.pending , mpesa_response_data['MerchantRequestID'] , mpesa_response_data['CheckoutRequestID'] )
        if not db_new_transaction:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "failed to create the new transaction on stk push")
        return {
            'check_out_id' : db_new_transaction.merchant_checkout_id, # we are returing this for now for the case of debugging and error anlaysis 

            }
    else :
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , detail = 'mpesa return error string code instead of 0')

@router.post('/callback')  # Changed to POST
async def deposit_call_back_response(db: db_dependancy, request: Request):
    try:
        data = await request.json()
        print(f"Raw callback data: {data}")

        # Extract callback data safely
        stk_callback = data.get("Body", {}).get("stkCallback", {})
        if not stk_callback:
            logger.error("No stkCallback found in request body")
            return {"error": "Invalid callback format"}

        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")

        if not merchant_request_id:
            logger.error("No MerchantRequestID found in callback")
            return {"error": "Missing MerchantRequestID"}

        # Extract receipt number safely
        callback_metadata = stk_callback.get("CallbackMetadata", {})
        metadata_items = callback_metadata.get("Item", [])
        
        receipt_number = None
        for item in metadata_items:
            if item.get("Name") == "MpesaReceiptNumber":
                receipt_number = item.get("Value")
                break

        print(f"Processing callback - MerchantRequestID: {merchant_request_id}, ResultCode: {result_code}, Receipt: {receipt_number}")

        if result_code == 0:  # Success
            if not receipt_number:
                logger.error(f"Successful transaction but no receipt number found for {merchant_request_id}")
                receipt_number = "MISSING_RECEIPT"
            
            # Update transaction as successful
            success_db_transaction = await update_transaction(
                db, 
                trans_status.successfull,  # Fixed: use trans_status not trans_type
                merchant_request_id, 
                receipt_number
            )
            
            if not success_db_transaction:
                logger.error(f"Failed to update transaction {merchant_request_id}")
                raise HTTPException(status_code=500, detail="Failed to update transaction")
            
            # Update account balance
            updated_account = await update_account(
                db, 
                success_db_transaction.account_id, 
                trans_type.deposit, 
                success_db_transaction.amount
            )
            
            if not updated_account:
                logger.error(f"Failed to update account for transaction {merchant_request_id}")
                raise HTTPException(status_code=500, detail="Failed to update account")
            
            logger.info(f"Transaction {merchant_request_id} processed successfully with receipt {receipt_number}")
            return {"success": "ok"}
            
        else:  # Failed transaction
            logger.info(f"Transaction {merchant_request_id} failed with result code {result_code}")
            failed_transaction = await update_transaction(
                db, 
                trans_status.failed,  # Fixed: use trans_status
                merchant_request_id, 
                "FAILED_TRANSACTION"
            )
            
            if not failed_transaction:
                logger.error(f"Failed to log failed transaction {merchant_request_id}")
                raise HTTPException(status_code=500, detail="Failed to log failed transaction")
            
            return {"error": "Transaction failed"}

    except Exception as e:
        logger.error(f"Callback processing failed: {str(e)}", exc_info=True)
        return {"error": "Callback processing failed"}

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

@router.post('/withdrawal')
async def withdrawal_request(db: db_dependancy, user: user_depencancy, user_transaction_request_data: CreateTransaction):
    """Initiate withdrawal request"""
    try:
        user_id = user.get('user_id')
        
        # Get user and account data
        user_and_account_data = await get_user_and_account_data(db, user_id)
        if not user_and_account_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User account not found"
            )
        
        # Check if user has sufficient balance
        if user_and_account_data.account.balance < user_transaction_request_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance for withdrawal"
            )
        
        # Minimum withdrawal check
        if user_transaction_request_data.amount < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum withdrawal amount is 10 KES"
            )
        
        # In production, use user_and_account_data.phone
        test_phone = '254724027231'
        
        # Send B2C request
        b2c_instance = B2CPaymentService()
        response = await b2c_instance.send_b2c_request(
            user_transaction_request_data.amount, 
            test_phone
        )
        
        if response.get('ResponseCode') == '0':
            # Create pending transaction
            db_transaction = await create_withdrawal_transaction(
                db, 
                user_transaction_request_data,
                user_and_account_data.id,
                user_and_account_data.account.id, 
                trans_status.pending,
                response.get('ConversationID'),  
                response.get('OriginatorConversationID')
            )
            
            if not db_transaction:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail="Failed to create transaction record"
                )
            
            return {
                'message': 'Withdrawal request submitted successfully',
                'conversation_id': response.get('ConversationID'),
                'status': 'pending'
            }
        else:
            # Log the failed response
            logger.error(f'B2C request failed: {response}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Withdrawal request failed: {response.get('ResponseDescription', 'Unknown error')}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f'Withdrawal endpoint failed: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during withdrawal processing"
        ) 

@router.post('/withdrawal/result')
async def withdrawal_result_callback(db: db_dependancy, request: Request):
    """
    Handles successful and failed B2C transaction results
    """ 
    try:
        data = await request.json()
        logger.info(f"B2C Result callback: {data}")
        
        result = data.get('Result', {})
        conversation_id = result.get('ConversationID')
        result_code = result.get('ResultCode')
        result_description = result.get('ResultDesc', '')
        
        if not conversation_id:
            logger.error("No ConversationID in result callback")
            return {"error": "Invalid callback format"}
        
        if result_code == 0:  # Success
            # Extract receipt
            parameters = result.get('ResultParameters', {}).get('ResultParameter', [])
            receipt = next(
                (param['Value'] for param in parameters if param['Key'] == 'TransactionReceipt'),
                None
            )
            
            # Update as successful
            updated_transaction = await update_b2c_transaction(
                db, conversation_id, trans_status.successfull, receipt
            )
            
            # Update account balance
            await update_account(
                db, updated_transaction.account_id, 
                trans_type.withdrawal, updated_transaction.amount
            )
            
            logger.info(f"Withdrawal {conversation_id} completed successfully")
            return {"success": "Transaction completed"}
            
        else:  # Failed but processed
            # Update as failed
            await update_b2c_transaction(
                db, conversation_id, trans_status.failed, None
            )
            
            logger.info(f"Withdrawal {conversation_id} failed: {result_description}")
            return {"error": f"Transaction failed: {result_description}"}
            
    except Exception as e:
        logger.error(f"Result callback processing failed: {e}", exc_info=True)
        return {"error": "Callback processing failed"}


@router.post('/withdrawal/timeout')
async def withdrawal_timeout_callback(db: db_dependancy, request: Request):
    """
    Handles B2C transaction timeouts and system failures
    """
    try:
        data = await request.json()
        logger.info(f"B2C Timeout callback: {data}")
        
        result = data.get('Result', {})
        conversation_id = result.get('ConversationID')
        result_description = result.get('ResultDesc', 'Transaction timed out')
        
        if not conversation_id:
            logger.error("No ConversationID in timeout callback")
            return {"error": "Invalid callback format"}
        
        # Update transaction as failed due to timeout
        await update_b2c_transaction(
            db, conversation_id, trans_status.failed, None
        )
        
        logger.info(f"Withdrawal {conversation_id} timed out: {result_description}")
        return {"error": f"Transaction timed out: {result_description}"}
        
    except Exception as e:
        logger.error(f"Timeout callback processing failed: {e}", exc_info=True)
        return {"error": "Timeout callback processing failed"}

    
# UTILITY FUNCTION FOR HELLPING IN TRANSACTION API FUNCTIONS    
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
      logger.error(f'failed to parse the b2c response data {e}')
      raise RuntimeError(f'there was a problem with the data parsing logic for the result logic on ')

  else :
    result_data = data['Result']
    result_description = result_data.get('ResultDesc')
    ConversationID = result_data.get('ConversationID')
    return {'result_description' : result_description , 'ConversationID' : ConversationID}