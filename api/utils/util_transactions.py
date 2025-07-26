from fastapi import HTTPException , status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from pydantic_schemas.transaction_schemas import CreateTransaction , TransactionGeneral, trans_status, trans_type
from db.models.model_users import Account, Transaction

""" outdated
async def add_transaction(db : AsyncSession , user_data : CreateTransaction , user_id : int , account_id : int):
    db_transaction = Transaction(
        user_id = user_id,
        account_id = account_id,
        amount = user_data.amount,
        transaction_type = user_data.transaction_type,
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction
"""


async def create_transaction(db : AsyncSession ,
 transaction_data : CreateTransaction ,
 user_id : int , 
 account_id : int ,
 status : trans_status,
 merchant_request_id : str ,
 merchant_checkout_id : str):
    db_transaction = Transaction(
        user_id = user_id,
        account_id = account_id,
        amount = transaction_data.amount,
        transaction_type = transaction_data.transaction_type,
        status = status,
        merchant_request_id = merchant_request_id,
        merchant_checkout_id = merchant_checkout_id,
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction 

async def get_current_transaction(db : AsyncSession , merchant_request_id : str):
    query = select(Transaction).where(Transaction.merchant_request_id == merchant_request_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_transaction(db : AsyncSession , status : trans_status , merchant_request_id : str , receipt_number : str):
    """search for the transaction using merchant checkout id 
        we will then update it to read either successfull or failed based n the status input 
    """
    current_transaction = await get_current_transaction(db , merchant_request_id)
    # now we will update it with new values from the user
    current_transaction.status = status
    current_transaction.receipt_number = receipt_number
    # after the update we then add an commit it to the databae 
    await db.commit()
    await db.refresh(current_transaction)
    return current_transaction

async def get_transaction_by_checkout_id(db : AsyncSession , checkout_id : str):
    query = select(Transaction).where(Transaction.merchant_checkout_id == checkout_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_transaction_and_account_data(db : AsyncSession , checkout_id : str):
    db_transaction = await get_transaction_by_checkout_id(db , checkout_id)
    query = select(Account).options(selectinload(Account.account)).where(Account.id == db_transaction.account_id)
    result = await db.execute(query)
    return result.scalars().first()

# these down here I belive will now be for the withdrawal transactions 

async def create_withdrawal_transaction(db : AsyncSession ,
transaction_data : CreateTransaction ,
user_id : int,
account_id : int,
status : trans_status,
ConversationID : str, 
OriginatorConversationID : str):
    db_transaction = Transaction(
        user_id = user_id,
        account_id = account_id,
        amount = transaction_data.amount,
        transaction_type = transaction_data.transaction_type,
        status = status,
        ConversationID = ConversationID,
        OriginatorConversationID = OriginatorConversationID,
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

async def get_transaction_by_ConversationID(db : AsyncSession , ConversationID : str):
    query = select(Transaction).where(Transaction.ConversationID == ConversationID)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_b2c_transaction(db : AsyncSession , ConversationID : str  , status : trans_status , receipt : str = None ):
    current_transaction = get_transaction_by_ConversationID( db , ConversationID)
    if not current_transaction:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR , detail = "error loading current user from the database")
    # after loadnig the transaction object from the database we will update its values with the new values
    current_transaction.status = status
    current_transaction.receipt = receipt
    await db.commit()
    await db.refresh(current_transaction)
    return current_transaction