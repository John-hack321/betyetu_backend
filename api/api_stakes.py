from fastapi import status, HTTPException, APIRouter

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.dependancies import db_dependancy, user_depencancy
from api.utils.util_stakes import get_stake_by_invite_code_from_db
from pydantic_schemas.stake_schemas import GuestStakeJoiningPayload, OwnerStakeInitiationPayload, StakeBaseModel, StakeInitiationPayload, StakeObject, StakeStatus, StakeWinner, StakesReturnObject
from services.staking_service.staking_service import StakingService
from pydantic_schemas.stake_schemas import StakeObject
from api.utils.util_stakes import get_user_stakes_where_user_is_owner_from_db, get_user_stakes_where_user_is_guest_from_db

logger= logging.getLogger(__name__)

router= APIRouter(
    prefix="/stakes",
    tags=['/stakes']
)

@router.get('/get_stake_data')
async def get_stake_data_by_invite_code(db: db_dependancy, invite_code: str) -> StakeDataObject:
    try :
        db_object= await get_stake_by_invite_code_from_db(db, invite_code)
        if not db_object:
            logger.error(f"an error occured while getting stake data from db: __get_stake_data_by_invite_code")
            raise RuntimeError('an error occured while fetching stake object from the database')
        stake_data= StakeDataObject(
            matchId= db_object.match_id,
            stakeId= db_object.id,
            homeTeam= db_object.home,
            awayTeam= db_object.away,
            stakeOwner= {"stakeAmount": db_object.amount, "stakePlacement": db_object.placement},
            stakeGeust= {'stakeAmont': db_object.invited_user_amount, "stakePlacement": db_object.invited_user_placement}
        )

        return stake_data
        
    except Exception as e:
        logger.error(f"an error occured: get_stake_data_by_invite_code, detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"an error occured: __get_stake_data_by_invite_code, api_stakes detail: {str(e)}")

@router.post('/initiate_stake')
async def initiate_stake(db : db_dependancy, user: user_depencancy, stake_initiation_payload: OwnerStakeInitiationPayload):
    try:
        staking_service= StakingService(user.get('user_id'))
        invite_code= await staking_service.owner_initiate_stake(db, stake_initiation_payload )
        if not invite_code:
            logger.error(f'the staking service failed to produce a valid payload')

        return {
            "status": status.HTTP_200_OK,
            "message": "stake has been initiated successfuly",
            "data" : {
                "invite_code": invite_code,
            }
        }
    except Exception as e: 
        logger.error(f'an error occured: __initeate_stake detail: {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"an error occured: __initiate_stake, {str(e)}")


@router.post('/join_initiated_stake')
async def join_initiated_stake(db : db_dependancy, user: user_depencancy, guest_stake_data: GuestStakeJoiningPayload):
    try:
        staking_service= StakingService(user.get('user_id'))
        join_stake_response= await staking_service.join_initiated_stake(db, guest_stake_data)
        
        return join_stake_response

    except Exception as e:
        logger.error(f'an error occured: __join_initiated_stake  detail: {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"an error occured: __join_initiated_stake, detail {str(e)}")


@router.get('/get_user_stakes')
async def get_user_stakes(db: db_dependancy, user: user_depencancy):
    try:
        db_owner_stakes= await get_user_stakes_where_user_is_owner_from_db(db, user.get('user_id'))
        if not db_owner_stakes:
            logger.error(f'an error occured db_owner_stakes: object returned is not expected')
        db_guest_stakes= await get_user_stakes_where_user_is_guest_from_db(db, user.get('user_id'))
        if not db_guest_stakes:
            logger.error(f'an error occured __db_guest-stakes: object returned is not expected')

        stakes_return_data= await process_stakes_data(db_owner_stakes, db_guest_stakes)

        return stakes_return_data

    except Exception as e:
        logger.error(f"an unexpected error occured: __get_user_stakes: detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail= f"an unexpected error occured: __get_user_stakes: detail {str(e)}")




# UTILITY FUNCTIONS FOR AIDING THE STAKE API ENDPONTS

# TODO : implement pagination concept for the stakes api endpoint
# TODO : make the stakes data processing endpoint to sort the data as it is added to the stakes object beofre sending back to frontend
"""
processes the stakes data from the db 
return an object that is easier to return to the frontend
"""
async def process_stakes_data(owner_stakes: list[StakeBaseModel], guest_stakes: list[StakeBaseModel]):
    try: 
        general_stakes_object: StakesReturnObject= {}

        # loop through the owner stakes
        try :
            for item in owner_stakes:
                if item.winner== StakeWinner.owner:
                    result= 'won'
                else : 
                    result= "lost"
                data= StakeObject(
                    stakeId= item.id,
                    home= item.home,
                    away= item.away,
                    stakeAmount= item.amount,
                    stakeStatus= item.stake_status,
                    stakeResult= result,
                    date= item.created_at.isoformat(),
                )

                general_stakes_object.stakeData.append(data)
        except:
            logger.error(f'an error occured: __process_stakes_data while looping through owner_stakes: details: {str(e)}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f'an error occured while looping through the stake owner data: {str(e)}')

        # loop through the guest stakes now
        try: 
            for item in guest_stakes:
                if item.winner== StakeWinner.guest:
                    result= 'won'
                else :
                    result= 'lost'
                
                data= StakeObject(
                    stakeId= item.id,
                    home= item.home,
                    away= item.away,
                    stakeAmount= item.invited_user_amount,
                    stakeStatus= item.stake_status,
                    stakeResult= result,
                    date= item.created_at.isoformat(),
                )

            general_stakes_object.stakeData.append(data)
        except Exception as e:
            logger.error(f'an unexpected error occured: looping through guest_stakes, detail: {str(e)}')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f'an unexpected error occured: looping through the guest_stake, {str(e)} ')

        #before we return the data we will sort by the time of creation: created_at
        general_stakes_object.stakeData.sort(key=lambda x: x.date, reverse=True)
        
        general_stakes_object.status= status.HTTP_200_OK
        general_stakes_object.message= "the user stakes data has been retreived succesfuly"

        return general_stakes_object
    except Exception as e:
        logger.error(f'an unexpected error occured: __proccess_stakes_data, {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail= f'an unexpected error occured: __process_stakes_data, {str(e)} ')
