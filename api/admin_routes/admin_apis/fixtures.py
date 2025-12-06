from fastapi import APIRouter, Depends, HTTPException, status
from db.models.model_stakes import Stake
from db.models.model_fixtures import Fixture
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from sqlalchemy import delete
from typing import Dict, Any

import logging
import sys

from api.utils.dependancies import db_dependancy
from db.db_setup import get_db
from api.admin_routes.util_matches import delete_match_from_db, delete_matches_by_league_id
from api.admin_routes.util_leagues import delete_league_from_popular_leagues_table, update_league_added_status_to_true_or_false

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