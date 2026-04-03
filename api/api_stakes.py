from fastapi import status, HTTPException, APIRouter

import logging
import sys
import json

from api.utils.dependancies import db_dependancy, user_dependancy
from api.utils.util_stakes import get_stake_by_invite_code_from_db
from pydantic_schemas.stake_schemas import (
    GuestStakeJoiningPayload,
    OwnerStakeInitiationPayload,
    StakeBaseModel,
    StakeGeust,
    UserStakeObject,
    AdminStakeObject,
    UserStakesReturnObject,
    AdminStakesReturnObject,
    StakeDataObject,
    StakeOwner,
    StakeStatus,
    StakeWinner,
)
from services.staking_service.staking_service import StakingService, inviteCodeModel
from api.utils.util_stakes import (
    get_user_stakes_where_user_is_owner_from_db,
    get_user_stakes_where_user_is_guest_from_db,
    get_public_stakes_from_db,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stakes",
    tags=['stakes']
)


@router.get('/get_stake_data')
async def get_stake_data_by_invite_code(db: db_dependancy, user: user_dependancy, invite_code: str):
    print(f'the get stakes data by invite code has been reached by user of details : ', user)
    try:
        db_object = await get_stake_by_invite_code_from_db(db, invite_code)
        if not db_object:
            logger.error(f"an error occured while getting stake data from db: __get_stake_data_by_invite_code")
            raise RuntimeError('an error occured while fetching stake object from the database')

        stake_data = StakeDataObject(
            matchId=db_object.match_id,
            stakeId=db_object.id,
            homeTeam=db_object.home,
            awayTeam=db_object.away,
            stakeOwner=StakeOwner(stakeAmount=db_object.amount, stakePlacement=db_object.placement),
            stakeGeust=StakeGeust(stakeAmount=db_object.invited_user_amount, stakePlacement=db_object.invited_user_placement),
        )

        return stake_data

    except Exception as e:
        logger.error(f"an error occured: get_stake_data_by_invite_code, detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"an error occured: __get_stake_data_by_invite_code, api_stakes detail: {str(e)}")


@router.post('/initiate_stake')
async def initiate_stake(db: db_dependancy, user: user_dependancy, stake_initiation_payload: OwnerStakeInitiationPayload):
    try:
        staking_service = StakingService(user.get('user_id'))
        print(f"the stake initiation payload has been reached by the user {user.get('user_id')}")

        invite_code_object: inviteCodeModel = await staking_service.owner_initiate_stake(db, stake_initiation_payload)
        print(f"the invite code gotten from staking service is: {invite_code_object.inviteCode}")

        if not invite_code_object:
            logger.error(f'the staking service failed to produce a valid payload')

        return invite_code_object

    except Exception as e:
        await db.rollback()
        logger.error(f'an error occured: __initeate_stake detail: {str(e)}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured: __initiate_stake, {str(e)}")


@router.post('/cancel_stake')
async def cancel_stake_placement_stake_owner_scenario(db: db_dependancy, user: user_dependancy, invite_code: str):
    logger.info(f'the stake cancelation route has been accessed with data : {invite_code}')
    try:
        staking_service = StakingService(user.get("user_id"))
        cancellation_response = await staking_service.owner_cancel_stake()
        return cancellation_response

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"an error occured whle canelling stake placement: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while cancelling stake from db: {str(e)}"
        )


@router.post('/join_initiated_stake')
async def join_initiated_stake(db: db_dependancy, user: user_dependancy, guest_stake_data: GuestStakeJoiningPayload):
    try:
        print(f"user of username : {user.get('username')} has just accessed the join initiated stake endpint")
        print(f"the data he has acessed the endpint with is :", json.dumps(guest_stake_data.model_dump(), indent=4, default=str))

        staking_service = StakingService(user.get('user_id'))
        join_stake_response = await staking_service.join_initiated_stake(db, guest_stake_data)

        return join_stake_response

    except Exception as e:
        logger.error(f'an error occured: __join_initiated_stake  detail: {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"an error occured: __join_initiated_stake, detail {str(e)}")


@router.get('/get_user_stakes')
async def get_user_stakes(db: db_dependancy, user: user_dependancy):
    """
    this is the main function for letting the user to get all stakes available
    """
    try:
        db_owner_stakes = await get_user_stakes_where_user_is_owner_from_db(db, user.get('user_id'))
        if db_owner_stakes is None:
            logger.error(f'an error occured db_owner_stakes: object returned is not expected')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get owner stakes from the database"
            )

        db_guest_stakes = await get_user_stakes_where_user_is_guest_from_db(db, user.get('user_id'))
        if db_guest_stakes is None:
            logger.error(f'an error occured __db_guest_stakes: object returned is not expected')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get guest stakes from the database"
            )

        stakes_return_data = await process_stakes_data(db_owner_stakes, db_guest_stakes)
        return stakes_return_data.stakeData

    except Exception as e:
        logger.error(f"an unexpected error occured: __get_user_stakes: detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"an unexpected error occured: __get_user_stakes: detail {str(e)}")


@router.get('/get_all_available_public_stakes')
async def get_all_available_public_stakes_function(db: db_dependancy, user: user_dependancy, page: int = 1, limit: int = 100):
    try:
        if page < 1:
            logger.error(f"page given : {page} is less then 1 ")
        if limit < 1 or limit > 100:
            logger.error(f"limit can only be in between 1 and 100 , limit given : {limit}")

        public_stakes_data = await get_public_stakes_from_db(db, page, limit)
        if not public_stakes_data:
            logger.error(f"the data returned from the database is empty ")

        return public_stakes_data

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"an unexpected error occured while getting all availabe public stakes : {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while trying to fetch the availabe public stakes : {str(e)}"
        )


# ── Utility: process stakes into frontend-ready objects ───────────────────────

def _resolve_result_for_owner(item) -> str:
    if item.winner is None:
        return "pending"
    return "won" if item.winner == StakeWinner.owner else "lost"


def _resolve_result_for_guest(item) -> str:
    if item.winner is None:
        return "pending"
    return "won" if item.winner == StakeWinner.guest else "lost"


def _resolve_status(item) -> str:
    if item.stake_status == StakeStatus.successfull:
        return "successful"
    if item.stake_status == StakeStatus.progressing:
        return "progressing"
    return "pending"


def _resolve_possible_win(item) -> int | str:
    return item.possibleWin if item.possibleWin is not None else "pending"


async def process_stakes_data(
    owner_stakes: list,
    guest_stakes: list,
    admin: bool = False,
):
    """
    Processes raw DB stake rows into the correct response shape.

    - admin=False  →  returns UserStakesReturnObject  (stakeData: list[UserStakeObject])
    - admin=True   →  returns AdminStakesReturnObject (stakeData: list[AdminStakeObject])
    """
    try:
        if admin:
            result_obj = AdminStakesReturnObject(
                status="success",
                message="Stakes retrieved successfully",
                stakeData=[],
            )
        else:
            result_obj = UserStakesReturnObject(
                status="success",
                message="Stakes retrieved successfully",
                stakeData=[],
            )

        # Owner stakes 
        try:
            for item in owner_stakes:
                result = _resolve_result_for_owner(item)
                status_value = _resolve_status(item)
                possible_win = _resolve_possible_win(item)

                logger.info(f"owner stake {item.id}: status={status_value}, result={result}")

                if admin:
                    data = AdminStakeObject(
                        stakeId=item.id,
                        role="owner",
                        userId=item.user_id,
                        invited_user_id=item.invited_user_id,
                        amount=item.amount,
                        invited_user_amount=item.invited_user_amount,
                        match_id=item.match_id,
                        home=item.home,
                        away=item.away,
                        stakeType=item.public,
                        winner=result,
                        inviteCode=item.invite_code,
                        possibleWin=item.possibleWin,
                        stakeStatus=status_value,
                        placement=item.placement,
                    )
                else:
                    data = UserStakeObject(
                        stakeId=item.id,
                        home=item.home,
                        away=item.away,
                        stakeAmount=item.amount,
                        stakeStatus=status_value,
                        stakeResult=result,
                        date=item.created_at.isoformat(),
                        possibleWin=possible_win,
                        inviteCode=item.invite_code,
                        placement=item.placement,
                        public=item.public,
                    )

                result_obj.stakeData.append(data)

        except Exception as e:
            logger.error(f'An error occurred in process_stakes_data while processing owner stakes: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error processing stake owner data: {str(e)}'
            )

        # Guest stakes 
        try:
            for item in guest_stakes:
                result = _resolve_result_for_guest(item)
                status_value = _resolve_status(item)
                possible_win = _resolve_possible_win(item)

                logger.info(f"guest stake {item.id}: status={status_value}, result={result}")

                if admin:
                    data = AdminStakeObject(
                        stakeId=item.id,
                        role="guest",
                        userId=item.user_id,
                        invited_user_id=item.invited_user_id,
                        amount=item.amount,
                        invited_user_amount=item.invited_user_amount,
                        match_id=item.match_id,
                        home=item.home,
                        away=item.away,
                        stakeType=item.public,
                        winner=result,
                        inviteCode=item.invite_code,
                        possibleWin=item.possibleWin,
                        stakeStatus=status_value,
                        placement=item.placement,
                    )
                else:
                    data = UserStakeObject(
                        stakeId=item.id,
                        home=item.home,
                        away=item.away,
                        stakeAmount=item.amount,
                        stakeStatus=status_value,
                        stakeResult=result,
                        date=item.created_at.isoformat(),
                        possibleWin=possible_win,
                        placement=item.invited_user_placement,
                        public=item.public,
                    )

                result_obj.stakeData.append(data)

        except Exception as e:
            logger.error(f'An error occurred in process_stakes_data while processing guest stakes: {str(e)}', exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error processing guest stake data: {str(e)}'
            )

        # Sort by date (user path only — admin objects don't have a `date` field)
        if not admin:
            result_obj.stakeData.sort(key=lambda x: x.date, reverse=True)

        result_obj.status = str(status.HTTP_200_OK)
        result_obj.message = "the user stakes data has been retrieved successfully"

        return result_obj

    except Exception as e:
        logger.error(f'an unexpected error occured: __process_stakes_data, {str(e)}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'an unexpected error occured: __process_stakes_data, {str(e)}'
        )