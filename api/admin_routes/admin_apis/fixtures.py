from fastapi import APIRouter, Depends, HTTPException, status
from db.models.model_stakes import Stake
from db.models.model_fixtures import Fixture
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from sqlalchemy import delete
from typing import Dict, Any

import logging
import sys

from api.utils.dependancies import db_dependancy, user_depencancy
from db.db_setup import get_db
from api.admin_routes.util_matches import admin_log_live_match_scores, admin_make_match_live, delete_match_from_db, delete_matches_by_league_id
from api.admin_routes.util_leagues import delete_league_from_popular_leagues_table, update_league_added_status_to_true_or_false
from services.caching_services.redis_client import update_live_match_away_score, update_live_match_home_score
from services.sockets.socket_services import update_live_match_scores_on_frontend, update_match_to_live_and_update_live_data_on_frontend, update_match_to_live_on_frontend_with_live_data_too

router = APIRouter(
    prefix="/admin/fixtures",
    tags=["admin/fixtures"],
    responses={404: {"description": "Not found"}},
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)


@router.delete("/delete-all-matches", response_model=Dict[str, Any])
async def delete_all_matches(db: db_dependancy):
    """
    ⚠️ DANGER ZONE ⚠️
    
    Delete ALL matches and their associated stakes from the database.
    This is irreversible!
    
    Returns:
    - Count of deleted stakes and matches
    - Success message
    """
    try:
        logger.warning("ATTEMPTING TO DELETE ALL MATCHES AND STAKES FROM THE DATABASE")
        
        # Start a transaction
        await db.begin()
        
        # Step 1: Delete all stakes first (due to foreign key constraints)
        stakes_delete_result = await db.execute(delete(Stake))
        stakes_deleted_count = stakes_delete_result.rowcount
        
        logger.info(f"Deleted {stakes_deleted_count} stakes from the database")
        
        # Step 2: Delete all fixtures
        fixtures_delete_result = await db.execute(delete(Fixture))
        fixtures_deleted_count = fixtures_delete_result.rowcount
        
        logger.info(f"Deleted {fixtures_deleted_count} fixtures from the database")
        
        # Commit the transaction
        await db.commit()
        
        return {
            "status": "success",
            "message": "All matches and associated stakes have been deleted successfully",
            "deleted_counts": {
                "stakes": stakes_deleted_count,
                "fixtures": fixtures_deleted_count
            }
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting all matches: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting all matches: {str(e)}"
        )


@router.delete("/{match_id}", response_model=Dict[str, Any])
async def delete_match(
    match_id: int,
    db: db_dependancy,
):
    """
    Delete a match by its ID.
    
    - **match_id**: The ID of the match to delete
    
    Returns:
    - Success message if deleted
    - 404 if match not found
    - 500 if there's a server error
    """
    try:
        # First check if match exists
        match = await db.get(Fixture, match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match with ID {match_id} not found"
            )
        
        # Log the deletion attempt
        logger.info(f"Deleting match with ID: {match_id}")
        
        # Delete the match using the utility function
        success = await delete_match_from_db(
            db=db,
            match_id=match_id
        )
        
        if not success:
            logger.error(f"Failed to delete match with ID: {match_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete match with ID {match_id}"
            )
            
        logger.info(f"Successfully deleted match with ID: {match_id}")
        return {
            "status": "success",
            "message": f"Match with ID {match_id} has been deleted successfully"
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error deleting match with ID {match_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting match with ID {match_id}"
        )


@router.delete("/league/{league_id}")
async def delete_league_matches(
    league_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all matches for a specific league by league ID.
    
    - **league_id**: The ID of the league whose matches should be deleted
    
    Returns:
    - Success message with count of deleted matches
    - 500 if there's a server error
    """
    try:
        logger.info(f"Attempting to delete all matches for league ID: {league_id}")
        
        # Delete all matches for the league
        deleted_count = await delete_matches_by_league_id(
            db=db,
            league_id=league_id
        )
        
        # Update the league's added status to False
        await update_league_added_status_to_true_or_false(
            db=db,
            league_id=league_id,
            added=False
        )
        
        # Remove from popular leagues if it exists there
        await delete_league_from_popular_leagues_table(db=db, league_id=league_id)
        
        logger.info(f"Successfully deleted {deleted_count} matches for league ID: {league_id}")
        
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} matches for league ID {league_id}",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting matches for league ID {league_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting matches for league ID {league_id}"
        )


# since we can not always afford to pay for apis or just for the part where we are starting before we afford actual api we might need to have dp manual logging of matches that are currently bing played

@router.post('/make_match_live_and_start_logging')
async def make_match_live_and_start_logging_match_with_live_data(db: db_dependancy, match_id: int):
    try :
        db_match_object= await admin_make_match_live(db, match_id)
        if not db_match_object:
            logger.error(f"an error occured while admin trying to make match live")


        await update_match_to_live_and_update_live_data_on_frontend(match_id, score_string)

        # find the best way to tell the frontned of success , maybe use the response model at the top of the query thingy
        return {
            'status_code': status.HTTP_200_OK,
            'message': 'message has been successfulu madelive'
        }

    except HTTPException:
        raise 

    except Exception as e:
        
        logger.error(f"an error occured while trying to make match live and start logging : {str(e)}",
        exc_info=True, 
        extra={
            'affected_match': match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured whle trying to make mathc {match_id} live an logging live data for it , {str(e)}"
        )

@router.post('/log_live_match_scores')
async def log_live_match_scores(db: db_dependancy, match_id: int, score_string : str):
    try: 
        home_score, away_score= map(int, score_string.split(' - '))
        db_match_object= await admin_log_live_match_scores(db, match_id, home_score, away_score)

        if not db_match_object:
            logger.error(f"an error occured while trying to log match with live data")
        
        # NOTE: after logging the data in the db we need to send updates to the users to via socketio

        logger.info(f"now sending live match updates to the frontend via socketio")
        await update_live_match_scores_on_frontend(match_id, score_string)

    except HTTPException:
        raise 

    except Exception as e:
        
        logger.error(f"an error occured while trying to log live match scores : {str(e)}",
        exc_info=True, 
        extra={
            'affected_match': match_id
        })

        raise HTTPException(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail= f"an error occured whle trying to log live match scores for match of id {match_id},  {str(e)}"
        )