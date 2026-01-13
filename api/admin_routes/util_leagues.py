from attr import exceptions
from fastapi import HTTPException , status

from db.models.model_leagues import League , PopularLeague
from pydantic_schemas.league_schemas import LeagueBaseModel
from api.utils.dependancies import user_dependancy , db_dependancy
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

async def add_league_to_popular_leagues(db: AsyncSession, league_id: int):
    # First, get the league from the database
    league = await get_league_by_id_from_db(db, league_id)
    
    if not league:
        logger.error(f"League with ID {league_id} not found in the database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {league_id} not found"
        )
    
    # Check if the league is already in the popular leagues
    existing_popular_league = await db.execute(
        select(PopularLeague).where(PopularLeague.id == league_id)
    )
    existing_popular_league = existing_popular_league.scalar_one_or_none()
    
    if existing_popular_league:
        logger.info(f"League with ID {league_id} is already in popular leagues")
        return existing_popular_league
    
    # Create a new PopularLeague entry
    db_object = PopularLeague(
        id=league.id,
        name=league.name,
        localized_name=league.localized_name,
        logo_url=league.logo_url,
        fixture_added=True,
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


async def get_popular_leageus_ids_from_db(db: AsyncSession):
    try: 
        query= select(PopularLeague)
        result= await db.execute(query)
        db_popular_leageus_object= result.scalars().all()

        leagues_ids_list= []
        for item in db_popular_leageus_object:
            leagues_ids_list.append(item.id)

        return leagues_ids_list

    except Exception as e:
        logger.error(f"an error occured while getting popular leagues list from the db {str(e)}",
        exc_info=True,
        detail={})

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an errro occured while getting popular leagues ids form the database"
        )