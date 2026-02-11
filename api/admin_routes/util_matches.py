from datetime import datetime, timezone, timedelta
from sys import exc_info

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from db.db_setup import Base
from pydantic_schemas.fixtures_schemas import FixtureScoreResponse, MatchObject
from db.models.model_fixtures import Fixture
from db.models.model_leagues import League
from db.models.model_fixtures import FixtureStatus

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status

import math
import logging
import sys

from pytz import timezone

from pydantic_schemas.live_data import ParsedScoreData
NAIROBI_TZ = timezone('Africa/Nairobi')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)


logger = logging.getLogger(__name__)

# this is solely for the admin
async def add_match_to_db(db : AsyncSession , match_data : MatchObject, season_id: int):

    db_object = Fixture(
        match_id= match_data.match_id,
        league_id=match_data.league_id,
        home_team_id= match_data.home_team_id,
        home_team= match_data.home_team,
        away_team_id= match_data.away_team_id,
        away_team= match_data.away_team,
        match_date= match_data.match_date,
        is_played= match_data.is_played,
        outcome= match_data.outcome,
        home_score= match_data.home_score,
        away_score= match_data.away_score,
        fixture_status= match_data.fixture_status,
        winner= match_data.winner,
        season_id= season_id
    )

    db.add(db_object)
    await db.commit()
    await db.refresh(db_object)
    return db_object

"""
the function will be sending the fixture data to the frontend in chunks of 100 per page 
"""
async def get_all_fixtures_from_db(db : AsyncSession , limit : int=100, page : int = 1):
    offset = (page - 1) * limit
    total= await db.scalar(select(func.count()).select_from(Fixture))
    current_time_eat = datetime.now(NAIROBI_TZ).replace(tzinfo=None)

    match_cutoff_time = current_time_eat - timedelta(hours=2)

    query= (
        select(Fixture, League.name.label("league_name"), League.logo_url.label("league_logo_url"))
        .where(
            Fixture.fixture_status != FixtureStatus.expired,
            Fixture.match_date >= match_cutoff_time
        )
        .join(League, Fixture.league_id == League.id)
        .order_by(Fixture.match_date.asc()) # for sorting the data based on the dates they will be played
        .limit(limit)
        .offset(offset)
    )
    result= await db.execute(query)
    rows= result.all()    

    if not rows:
        logger.error('an unexpected error occured : no fixtures found in the get all fixtures from db')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR ,
            detail= "no fixtures found in the get_all_fixtures_from_db utility functoin "
        )
    
    fixtures = await convert_fixtures_result_object_from_to_db_desired_return_object(rows)

    return {
        "page" : page,
        "limit" : limit,
        "total" : total,
        "total_pages" : math.ceil(total / limit),
        "has_next_page" : (page * limit) < total,
        "data" : fixtures
    }


"""
i think this will only apply to the populare(available) leagues
"""
async def get_fixtures_by_leageu_id_from_db(db : AsyncSession , league_id : int):
    query= select(Fixture).where(Fixture.league_id == league_id)
    result = await db.execute(query)
    return result.scalars().all()

# for this one i think we will have to do error handling on the utility fuction too
async def update_fixture_to_live_on_db(db : AsyncSession, match_id: int):
    """
    updates the fixture status column to live on db
    """

    try:
        query= select(Fixture).where(Fixture.match_id== match_id)
        result= await db.execute(query)
        db_fixture_object= result.scalars().first()

        db_fixture_object.fixture_status= FixtureStatus.live

        await db.commit()
        await db.refresh(db_fixture_object)
        return db_fixture_object

    except Exception as e:
        
        logger.error(f"an error occured while updating fixture object in db, {str(e)}",

        exc_info=True,
        extra={
            "affected_match_id": match_id
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updathing the fixture object to live on db, {str(e)}"
        )

# for deletig many matches at once

async def update_match_with_match_ended_data(db: AsyncSession, ended_match_fixture):
    """
    things to update: outcome, home_score, away_score, fixture_status
    updates the data suggested up there on the fixtur object so that it is marked as ended 
    """
    try:
        query= select(Fixture).where(Fixture.match_id== ended_match_fixture.get("match_id"))
        result= await db.execute(query)
        db_fixture_object= result.scalars().first()

        db_fixture_object.home_score= ended_match_fixture.get("home_score")
        db_fixture_object.away_score= ended_match_fixture.get("away_score")
        db_fixture_object.outcome= ended_match_fixture.get("outcome")
        db_fixture_object.fixture_status= FixtureStatus.expired

        await db.commit()
        await db.refresh(db_fixture_object)

        return db_fixture_object

    except Exception as e:
        logger.error(f"an error occured while updating match with match ended data, {str(e)}",
        exc_info=True,
        extra={
            "affected_match_id": ended_match_fixture.get("match_id")
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating match with match ended data: {str(e)}"
        )

async def delete_match_from_db(db: AsyncSession, match_id: int) -> bool:
    """
    Deletes a match from the database by match_id
    Returns True if successful, False if match not found
    """
    try:
        # First check if the match exists
        result = await db.execute(select(Fixture).filter(Fixture.match_id == match_id))
        match = result.scalar_one_or_none()
        
        if not match:
            return False
            
        await db.delete(match)
        await db.commit()
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting match {match_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting match: {str(e)}"
        )


async def delete_matches_by_league_id(db: AsyncSession, league_id: int):
    """
    Deletes all matches for a specific league
    Returns a dictionary with the count of deleted matches and success status
    """
    try:

        result = await db.execute(
            select(Fixture).filter(Fixture.league_id == league_id)
        )
        matches = result.scalars().all()
        
        if not matches:
            return {
                "status": status.HTTP_200_OK,
                "message": f"No matches found for league ID {league_id}",
                "deleted_count": 0
            }
        
        # Delete all matches in a single transaction
        deleted_count = 0
        for match in matches:
            await db.delete(match)
            deleted_count += 1
        
        await db.commit()
        
        return {
            "status": status.HTTP_200_OK,
            "message": f"Successfully deleted {deleted_count} matches for league ID {league_id}",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting matches for league {league_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting matches: {str(e)}"
        )

# SOME UTILITY FUNCTIONS TO HELP THE DB_UTILITY_FUNCTION 
async def convert_fixtures_result_object_from_to_db_desired_return_object(rows):
    """
    takes in the all fixtures rows from db 
    processes them so that we return the desired fixtures object to the frontend for processing
    """
    try:
        fixtures_with_league_data = []
        for row in rows:
            # first conver the fixture row to a dict for easier prosessing
            # we need to return only the data we are in need of 
            fixture_dict= row[0].__dict__
            parsed_fixture_object = {}

            parsed_fixture_object['match_id']= fixture_dict.get('match_id')
            parsed_fixture_object['match_date']= fixture_dict.get('match_date')
            parsed_fixture_object['league_id']= fixture_dict.get('league_id')
            parsed_fixture_object['league_name']= row.league_name
            parsed_fixture_object['league_logo_url']= row.league_logo_url
            parsed_fixture_object['home_team_id']= fixture_dict.get('home_team_id')
            parsed_fixture_object['home_team']= fixture_dict.get('home_team')
            parsed_fixture_object['away_team_id']= fixture_dict.get('away_team_id')
            parsed_fixture_object['away_team']= fixture_dict.get('away_team')
            parsed_fixture_object['score_string']= fixture_dict.get('outcome')
            # we only send the fixture status only when the match is live : 
            if fixture_dict.get('fixture_status') == FixtureStatus.live:
                parsed_fixture_object['is_match_live']= True

            fixtures_with_league_data.append(parsed_fixture_object)
            
        return fixtures_with_league_data

    except Exception as e:
        logger.error(f"an error occured while converint to fixtur data to desirerable object:{str(e)}",
        exc_info=True,
        extra={

        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while converting fixture to desirerable fixtures object"
        )


async def update_fixture_data_and_determine_winner(db: AsyncSession, match_id: int, match_scores_data: FixtureScoreResponse | ParsedScoreData) -> str:
    """
    uses the match socores to determine the match outcome ( determine the winnig team)
    it update the fixture object in the db , with the winning team data 
    the it returns the winning team for processing of user data in the main parent function it works for
    """
    try:
        query= select(Fixture).where(Fixture.match_id == match_id)
        result= await db.execute(query)
        db_fixture_object= result.scalars().first()

        # first we updata the data on the db based on the scores
        for item in match_scores_data.response.scores:
            if item.id== db_fixture_object.home_team_id:
                db_fixture_object.home_score= item.score
            else: 
                db_fixture_object.away_score= item.score

        db_fixture_object.outcome= f"{db_fixture_object.home_score}-{db_fixture_object.away_score}"

        # determine the winner and update it too
        if db_fixture_object.home_score > db_fixture_object.away_score:
            db_fixture_object.winner= "home"
            winning_team= db_fixture_object.home_team
        elif db_fixture_object.away_score > db_fixture_object.home_score:
            db_fixture_object.winner= "away"
            winning_team= db_fixture_object.away_team
        else: 
            db_fixture_object.winner= "draw"
            winning_team= "draw"

        return winning_team

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while updating fixture data and determining the winner, {str(e)}",
        exc_info=True,
        extra= {
            "affected_match": match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while updating fxiture data and setting the winner"
        )


from datetime import datetime, timedelta
from sqlalchemy import and_
from pytz import timezone

NAIROBI_TZ = timezone('Africa/Nairobi')

async def get_todays_matches(db: AsyncSession):
    """
    Gets all matches scheduled between 1 PM today and 3 AM tomorrow.
    This function is designed to run daily at 1 PM.
    """
    try:
        now = datetime.now(NAIROBI_TZ)
        
        # TODO : find a way to handle cases where the server is restarted at around past midnight
        # Set start time to 1 PM today (or current time if after 1 PM)
        start_time = now.replace(hour=13, minute=0, second=0, microsecond=0) # this one sets the time to 1 pm that day.
        
        # I THINK FOR THIS PART i WILL HAVE TO MAKE THE START TIME TO BE AT 1 PM ALWAYS RIGHT. 
        # MAYBE LATER ON , i MIGHT GO TO THE EXTENT OF CHANGING IT TO ANOHTER TIME MAYBE
        
        # If we're before 1 PM, use today at 1 PM
        # If we're after 1 PM, use current time
        """
        if now < start_time:
            start_time = start_time
        else:
            start_time = now
        """
        
        # Set end time to 3 AM next day
        end_time = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
        
        # Convert to timezone-naive datetime (since your DB stores naive datetimes)
        start_time_naive = start_time.replace(tzinfo=None)
        end_time_naive = end_time.replace(tzinfo=None)
        
        logger.info(f"Fetching matches from {start_time_naive} to {end_time_naive}")
        
        # We then query matches that are withing the times we go up there
        query = select(Fixture).where(
            and_(
                Fixture.match_date >= start_time_naive,
                Fixture.match_date < end_time_naive,
                Fixture.fixture_status != FixtureStatus.expired  # Exclude already played matches
            )
        ).order_by(Fixture.match_date.asc())
        
        result = await db.execute(query)
        matches = result.scalars().all()
        
        logger.info(f"Found {len(matches)} matches scheduled for today's polling window")
        
        return matches

    except Exception as e:
        logger.error(
            f"An error occurred while getting today's matches from the database: {str(e)}",
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while getting today's matches from the database: {str(e)}"
        )

async def update_home_score_and_away_score_on_db(
    db: AsyncSession, 
    match_id: str, 
    home_score: int, 
    away_score: int, 
    fixture_status: FixtureStatus= None,
    determine_winner: bool= None):
    """
        updates home score and away score on db
        also determines winner of the match if asked
        also update fixutre Status if asked => these last two here are for matches that have ended
    """
    try:
        
        match_id_int= int(match_id)
        query= select(Fixture).where(Fixture.match_id== match_id_int)
        result= await db.execute(query)
        db_match_object= result.scalars().first()

        db_match_object.home_score= home_score
        db_match_object.away_score= away_score
        db_match_object.outcome= f"{home_score} - {away_score}"

        # fixture status will on ly be upated if it has been passed in
        if fixture_status != None:
            db_match_object.fixture_status= fixture_status

        if determine_winner != None:
            db_match_object.winner= await determine_match_winner(home_score, away_score)

        await db.commit()
        await db.refresh(db_match_object)
        return db_match_object

    except Exception as e :
        await db.rollback()

        logger.error(f"an error occured while updating the match scores on the database, {str(e)}", exc_info=True)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while updating home and away score on the db, {str(e)}"
        )


async def update_fixture_status_in_db(db: AsyncSession,match_id: str,  fixture_status: FixtureStatus):
    try :

        match_id_int= int(match_id)
        query= select(Fixture).where(Fixture.match_id == match_id_int)
        result= await db.execute(query)
        db_match_object= result.scalars().first()

        db_match_object.fixture_status= fixture_status

        await db.commit()
        await db.refresh(db_match_object)

        return db_match_object

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured while trying to update fixture of id {match_id} to {fixture_status}",
        exc_info=True, 
        extra={
            "affected_match": match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to update fixture status on the db"
        )

async def determine_match_winner(home_score: int, away_score: int) -> str:
    try: 
        if home_score > away_score:
            winner= "home"
        elif home_score < away_score:
            winner= "away"
        elif home_score == away_score:
            winner= "draw"
        else:
            winner= "draw"

        return winner

    except Exception as e:
        logger.error(f" an error occured while determing the match winner : {str(e)}",
        exc_info=True,)

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to update the match winner, {str(e)}"
        )


async def admin_make_match_live(db: AsyncSession, match_id: int):
    try:

        query= select(Fixture).where(Fixture.match_id== match_id)
        result= await db.execute(query)
        db_match_object= result.scalars().first()

        db_match_object.fixture_status= FixtureStatus.live

        await db.commit()
        await db.refresh(db_match_object)
        return db_match_object

    except HTTPException:
        raise 

    except Exception as e:
        
        await db.rollback()

        logger.error(f"an error occured while admin is trying to make match live in db, {str(e)}",
        exc_info=True,
        extra={
            'affected_match': match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while trying to make match a live match: {str(e)}"
        )


async def admin_log_live_match_scores(db: AsyncSession,  match_id: int, score_string: str, home_score: int, away_score: int):
    try:
        query= select(Fixture).where(Fixture.match_id== match_id)
        result= await db.execute(query)
        db_match_object= result.scalars().first()

        db_match_object.home_score= home_score
        db_match_object.away_score= away_score
        db_match_object.outcome= score_string

        await db.commit()
        await db.refresh(db_match_object)
        return db_match_object

    except HTTPException:
        raise 

    except Exception as e:
        
        await db.rollback()

        logger.error(f"an error occured while admin trying to log live matche scores it the db, {str(e)}",
        exc_info=True,
        extra={
            'affected_match': match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"an error occured while adming trying to log live match scores in the db: {str(e)}"
        )