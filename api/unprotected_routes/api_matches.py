from aiohttp import http_exceptions
import fastapi
from fastapi import APIRouter , status , HTTPException 

from api.unprotected_routes.utils.util_matches import unprotected_get_fixtures_list_from_db

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router= APIRouter(
    prefix="/unprotected",
    tags=['/unprotected']
)

@router.get('/all_fixtures')
async def unprotected_get_fixtures(db : AsyncSession):
    try:
        db_unprotected_get_fixtures_object = await unprotected_get_fixtures_list_from_db()
        if not db_unprotected_get_fixtures_object:
            raise HTTPException(f'an error occured on the unprotected_get_fixture_list_from_db object_returned : {db_unprotected_get_fixtures_object}')
    except Exception as e:
        logger.error(f'an unexpected error occured at the unprotected_get_fixtures endpont : {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR , 
        detail=f"an unexpeced error occured on the unprotected_get_fixtures endpoint {str(e)}")