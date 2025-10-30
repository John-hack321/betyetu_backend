from sqlalchemy.ext.asyncio import AsyncSession
from db.models.model_users import Account
from sqlalchemy.future import select
from api.utils.transaction_dependancies import update_balance
from pydantic_schemas.transaction_schemas import trans_type

async def update_account(db : AsyncSession , account_id : int , transaction_type : trans_type , amount : int):
    query = select(Account).where(Account.id == account_id )
    result = await db.execute(query)
    main_result = result.scalars().first()
    main_result.balance = await update_balance(balance=main_result.balance, amount=amount, transaction_type=transaction_type)
    await db.commit()
    await db.refresh(main_result)
    return main_result

async def increment_account_balance(db : AsyncSession , account_id : int , amount : int):
    query = select(Account).where(Account.id == account_id)
    result = await db.execute(query)
    actual_result = result.scalar_one_or_none()
    actual_result.balance = actual_result.balance + amount
    await db.commit()
    await db.refresh(actual_result)
    return actual_result

async def get_account_data_by_user_id(user_id: int, db : AsyncSession):
    query= select(Account).where(Account.user_id== user_id)
    result= await db.execute(query)
    return result.scalars().first()


async def subtract_stake_amount_from_db(db: AsyncSession, user_id: int, stake_amount: int):
    query= select(Account).where(Account.user_id == user_id)
    result= await db.execute(query)
    db_object= result.scalars().first()
    db_object.balance= db_object.balance- stake_amount
    await db.commit()
    await db.refresh(db_object)
    return db_object
    