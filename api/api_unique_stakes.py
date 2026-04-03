import fastapi
from fastapi import APIRouter

import logging
import sys

logger= logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

unique_stakes_router = APIRouter(
    prefix="/unique_stakes",
    tags=["unique_stakes"]
)

@unique_stakes_router.get("/")
async def user_get_unique_stakes():
    logger.info("Getting unique stakes")
    # TODO: Implement logic to get unique stakes
    pass

@unique_stakes_router.post("/")
async def user_create_event_based_unique_stake():
    logger.info("Creating event based unique stake")
    # TODO: Implement logic to create event based unique stake
    pass



