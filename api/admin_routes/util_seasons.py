from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models.model_seasons import Season

import logging 

logger= logging.getLogger(__name__)

async def db_get_all_seasons_object_list(db: AsyncSession):
    try:
        query= select(Season)
        result= await db.execute(query)
        db_seasons_list= result.scalars().all()
        return db_seasons_list

    except Exception as e:
        logger.error(f"an error occured while getting all seasons list from the db: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to get all seasons list from  the db: {str(e)}"
        )

async def db_create_new_season_in_db(db: AsyncSession, season_string: str):
    try:
        season_object= Season(
            season_year_string= season_string
        )
        db.add(season_object)
        await db.commit()
        await db.refresh(season_object)
        return season_object

    except Exception as e:
        logger.error(f"an error occured while to create a new season in the database : {str(e)}", exc_info= True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured while trying to creat a new season in the database"
        )