import fastapi
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select
from sqlalchemy.orm import query

from db.db_setup import Base
from db.models.model_chess_users import ChessProfile
from pydantic_schemas.chess_player_schemas import CreateChessDbProfile

async def add_new_chess_player(db : AsyncSession , user_chess_data : CreateChessDbProfile , user_id):
    new_chess_data = ChessProfile(
        user_id = user_id,
        player_id = user_chess_data.player_id,
        chess_username =  user_chess_data.chess_username,
        followers = user_chess_data.followers,
        country = user_chess_data.country,
        account_status = user_chess_data.account_status,
        account_verification_status = user_chess_data.account_verification_status,
        league =user_chess_data.league
    )
    db.add(new_chess_data)
    await db.commit()
    await db.refresh(new_chess_data)
    return new_chess_data


async def get_user_by_chess_foreign_username(db : AsyncSession , username : str):
    query = select(ChessProfile).where(ChessProfile.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()