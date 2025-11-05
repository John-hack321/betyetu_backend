from attr import exceptions
from fastapi import HTTPException , status

from db.models.model_leagues import League , PopularLeague
from pydantic_schemas.league_schemas import LeagueBaseModel
from api.utils.dependancies import user_depencancy , db_dependancy
from db.db_setup import Base

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import logging 

logger= logging.getLogger(__name__)



async def add_league_to_db(db : AsyncSession, league_data : LeagueBaseModel):
    db_league = League(
        id = league_data.id,
        name = league_data.name,
        localized_name = league_data.localized_name,
        logo_url = league_data.logo_url,
        fixture_added = False
    )

    db.add(db_league)
    await db.commit()
    await db.refresh(db_league)
    return db_league

async def get_leagues_list_from_db(db : AsyncSession):
    query = select(League)
    result = await db.execute(query)
    return result.scalars().all()

async def get_league_by_id_from_db(db : AsyncSession, league_id):
    query = select(League).where(League.id == league_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_popular_leagues_from_db(db : AsyncSession ):
    query = select(PopularLeague)
    result = await db.execute(query)
    return result.scalars().all()

async def add_league_to_popular_leagues(db : AsyncSession , league_object : LeagueBaseModel):
    db_object = PopularLeague(
        id=league_object.id,
        name=league_object.name,
        localized_name=league_object.localized_name,
        logo_url=league_object.logo_url,
        fixture_add=True,
    )
    db.add(db_object)
    await db.commit()
    await db.refresh(db_object)
    return db_object


async def update_league_fixture_status_to_true(db : AsyncSession , league_id):
    db_object = await get_league_by_id_from_db(db , league_id)
    if not db_object:
        logger.error(f'an unexpeceted error occured on the get_leauge_by_id_from_db object returned is not expected :  {db_object}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
        detail=f"an unexpected error in the update_league_fixtures_endpoint , get_league_by_id_from_db")
    db_object.fixture_added= True
    await db.commit()
    await db.refresh(db_object)
    return db_object


async def update_league_added_status_to_true_or_false(db: AsyncSession, league_id: int):
    try:
        query= select(League).where(League.id== league_id)
        result= await db.execute(query)
        db_league_object= result.scalars().first()

        if db_league_object.fixture_added == False:
            db_league_object.fixture_added= True
        
        if db_league_object.fixture_added == True:
            db_league_object.fixture_added= False
        
        await db.commit()
        await db.refresh(db_league_object)
        return db_league_object

    except Exception as e:
        await db.rollback()
        logger.error(f"an error occured: update_league_added: {str(e)}",
        exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating leageu added status to true"
        )


async def delete_league_from_popular_leagues_table(db: AsyncSession, league_id: int):
    try:
        query= select(League).where(League.id== league_id)
        result= await db.execute(query)
        db_popular_league_object= result.scalars().first()

        await db.delete(db_popular_league_object)
        await db.commit()

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured whle deleting leageu: {league_id} from the database: {str(e)}",
        exc_info=True,
        extra={
            "affected_league": league_id,
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while deleting league from popular leagues in the database: {str(e)}"
        )