import fastapi
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select
from sqlalchemy.orm import query

from db.db_setup import Base
from db.models.model_chess_users import ChessProfile
from pydantic_schemas.chess_player_schemas import CreateChessDbProfile , account_status_code

async def add_new_chess_player(db: AsyncSession, user_chess_data: dict, user_id: int):
    """
    Creates a new chess player profile from dictionary data returned by the chess service
    """
    # Convert dictionary data to the format expected by the database model
    new_chess_data = ChessProfile(
        user_id=user_id,
        player_id=user_chess_data.get('player_id'),
        username=user_chess_data.get('chess_username'),
        followers=user_chess_data.get('followers', 0),
        country=user_chess_data.get('country'),
        account_status=account_status_code.basic,  # Default to basic
        account_verification_status=user_chess_data.get('account_verification_status', False),
        league=user_chess_data.get('league', 'wood')
    )
    
    db.add(new_chess_data)
    await db.commit()
    await db.refresh(new_chess_data)
    return new_chess_data


async def get_user_by_chess_foreign_username(db: AsyncSession, username: str):
    query = select(ChessProfile).where(ChessProfile.username == username) 
    result = await db.execute(query)
    return result.scalar_one_or_none()