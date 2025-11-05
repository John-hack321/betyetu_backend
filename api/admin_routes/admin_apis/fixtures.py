from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
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
        deleted = await delete_match_from_db(db, match_id)
    
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Match with ID {match_id} not found"
            )
        
        return {
            "status": "success",
            "message": f"Match with ID {match_id} has been deleted successfully"
        }

    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"un unexpected error occured: delete match from db: {str(e)}",
        exc_info=True,)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while deleting a match from the database, {str(e)}"
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
        result = await delete_matches_by_league_id(db, league_id)
        if result.get("status") != status.HTTP_200_OK:
            logger.error(f"an error occured whle deleting matches by leageu id: {result.get("status")}")

        # upon deletion of the matches we need to remove / delete the leageu form the populare leageus table
        # first we need to update the fixture added part to false
        db_league_object= await update_league_added_status_to_true_or_false(db, league_id)
        if not db_league_object:
            logger.error(f"leageu object returned is not as expected: delete_matches_by_league_id: {db_league_object}")

        await delete_league_from_popular_leagues_table(db, league_id)
        

    except HTTPException as e:

        await db.rollback()

        raise

    except Exception as e:
        logger.error(f"Unexpected error deleting matches for league {league_id}: {str(e)}",
        exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

