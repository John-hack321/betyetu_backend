# we wanna create our first utility function for creating  a user here now 
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from pydantic_schemas.users_schema import UserCreateRequest
from db.models.model_users import User
from api.utils.dependancies import bcrypt_context



async def create_user(db : AsyncSession , user : UserCreateRequest):
    db_user = User(
        username = user.username,
        email = user.email,
        phone = user.phone,
        hashed_password = bcrypt_context.hash(user.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    print("table refreshed successfuly")
    return db_user

async def get_user_by_id(db : AsyncSession , user_id : int):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalars().first()

async def get_user_and_account_data(db: AsyncSession, user_id: int):
    query = select(User).options(selectinload(User.account)).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalars().first()