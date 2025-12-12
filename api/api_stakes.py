from fastapi import status, HTTPException, APIRouter

import logging
import sys
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.util import expand_column_list_from_order_by

from api.utils.dependancies import db_dependancy, user_depencancy
from api.utils.util_stakes import get_stake_by_invite_code_from_db
from pydantic_schemas.stake_schemas import GuestStakeJoiningPayload, OwnerStakeInitiationPayload, StakeBaseModel, StakeGeust, StakeInitiationPayload, StakeObject, StakeStatus, StakeWinner, StakesReturnObject, StakeDataObject, StakeOwner
from services.staking_service import staking_service
from services.staking_service.staking_service import StakingService, inviteCodeModel
from pydantic_schemas.stake_schemas import StakeObject
from api.utils.util_stakes import get_user_stakes_where_user_is_owner_from_db, get_user_stakes_where_user_is_guest_from_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger= logging.getLogger(__name__)

router= APIRouter(
    prefix="/stakes",
    tags=['stakes']
)

@router.get('/get_stake_data')
async def get_stake_data_by_invite_code(db: db_dependancy, user: user_depencancy, invite_code: str):
    print(f' the get stakes data by invite code has been reached by user of details : ', user)
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
            stakeOwner= StakeOwner(stakeAmount= db_object.amount, stakePlacement=db_object.placement),
            stakeGeust= StakeGeust(stakeAmount=db_object.invited_user_amount, stakePlacement=db_object.invited_user_placement),
        )

        print(f"stake data gottne fromt he endpoint is :", stake_data)

        return stake_data
        
    except Exception as e:
        logger.error(f"an error occured: get_stake_data_by_invite_code, detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail=f"an error occured: __get_stake_data_by_invite_code, api_stakes detail: {str(e)}")

@router.post('/initiate_stake')
async def initiate_stake(db : db_dependancy, user: user_depencancy, stake_initiation_payload: OwnerStakeInitiationPayload):
    try:
        staking_service= StakingService(user.get('user_id'))
        print(f"the stake initiation payload has been reached by the user {user.get("user_id")}")

        invite_code_object: inviteCodeModel = await staking_service.owner_initiate_stake(db, stake_initiation_payload )
        print(f"the invite code gotten from staking service is: {invite_code_object.inviteCode}")

        if not invite_code_object:
            logger.error(f'the staking service failed to produce a valid payload')

        print(f"invite code: {invite_code_object.inviteCode} has now been sent to the frontend")

        return invite_code_object

    except Exception as e: 

        await db.rollback()

        logger.error(f'an error occured: __initeate_stake detail: {str(e)}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"an error occured: __initiate_stake, {str(e)}")

@router.post('/cancel_stake')
async def cancel_stake_placement_stake_owner_scenario(db: db_dependancy, user: user_depencancy, invite_code: str):
    """
    this will be used for deleting / cancelling stake placement based on the invite code
    """
    
    logger.info(f'the stake cancelation route has been accessed with data : {invite_code}')

    try:
        staking_service= StakingService(user.get("user_id"))
        cancellation_response= await staking_service.owner_cancel_stake()
        
        return cancellation_response

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()

        logger.error(f"an error occured whle canelling stake placement: {str(e)}",
        exc_info=True,
        extra={
            "invite_code": invite_code
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"an error occured while cancelling stake from db: {str(e)}"
        )

@router.post('/join_initiated_stake')
async def join_initiated_stake(db : db_dependancy, user: user_depencancy, guest_stake_data: GuestStakeJoiningPayload):
    try:
        print(f"user of username : {user.get('username')} has just accessed the join initiated stake endpint")
        print(f"the data he has acessed the endpint with is :", json.dumps(guest_stake_data, indent=4, default=str))

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
        if db_owner_stakes == None:
            logger.error(f'an error occured db_owner_stakes: object returned is not expected, object return : {db_owner_stakes}')
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get woner stakes from the database"
            )

        db_guest_stakes= await get_user_stakes_where_user_is_guest_from_db(db, user.get('user_id'))
        if db_guest_stakes == None:
            logger.error(f'an error occured __db_guest-stakes: object returned is not expected: object returned : {db_guest_stakes}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to get guest stakes from the database"
            )

        stakes_return_data= await process_stakes_data(db_owner_stakes, db_guest_stakes)
        print(f"stake data to be sent back to the use is {stakes_return_data.stakeData}")

        # TODO: define a better way \ find a way to return the stakes data well with better handling
        return stakes_return_data.stakeData

    except Exception as e:
        logger.error(f"an unexpected error occured: __get_user_stakes: detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail= f"an unexpected error occured: __get_user_stakes: detail {str(e)}")




# UTILITY FUNCTIONS FOR AIDING THE STAKE API ENDPONTS

# TODO : implement pagination concept for the stakes api endpoint
"""
processes the stakes data from the db 
return an object that is easier to return to the frontend
"""
async def process_stakes_data(owner_stakes: list[StakeBaseModel], guest_stakes: list[StakeBaseModel]):
    try: 
        general_stakes_object = StakesReturnObject(
            status="success",
            message="Stakes retrieved successfully",
            stakeData=[]
        )

        # loop through the owner stakes to determine which stakes the user won
        try:
            for item in owner_stakes:
                result= "pending"
                if item.winner != None:
                    if item.winner == StakeWinner.owner:
                        result = 'won'
                    else: 
                        result = "lost"

                # Convert the stake status to the appropriate enum value

                status_value="pending"

                print(f"the value fo stake status from the database before manipulation is : {item.stake_status}")
                if item.stake_status == StakeStatus.pending:
                    status_value= "pending"
                elif item.stake_status == StakeStatus.successfull:
                    status_value= "successful"
                print(f"analys of stake status hs been done and the value of the stakeStatus has been set to {status_value}")

                possible_win: str | int= 0
                if item.possibleWin== None:
                    possible_win= "pending"
                else:
                    possible_win= item.possibleWin
                
                data = StakeObject(
                    stakeId=item.id,
                    home=item.home,
                    away=item.away,
                    stakeAmount=item.amount,
                    stakeStatus=status_value,
                    stakeResult=result,
                    date=item.created_at.isoformat(),
                    possibleWin=possible_win,
                    inviteCode= item.invite_code,
                    placement= item.placement,
                )

                print(f"stake data to be sent is {data.stakeAmount, data.away, data.home, data.stakeAmount, data.stakeResult, data.stakeStatus, data.date, data.stakeId}")

                general_stakes_object.stakeData.append(data)
        except Exception as e:  # Properly catch the exception
            logger.error(f'An error occurred in __process_stakes_data while processing owner stakes: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error processing stake owner data: {str(e)}'
            )

        # loop through the guest stakes now
        try: 
            for item in guest_stakes:
                result="pending"
                if item.winner != None: # we have to do this so that if the colum is blank we dont asgn winners or losser
                    if item.winner == StakeWinner.guest:
                        result = 'won'
                    else: 
                        result = "lost"

                status_value= "pending"

                print(f"the value fo stake status from the database before manipulation is : {item.stake_status}")
                if item.stake_status == StakeStatus.pending:
                    status_value= "pending"
                elif item.stake_status == StakeStatus.successfull:
                    status_value= "successful"

                possible_win: str | int= 0
                if item.possibleWin== None:
                    possible_win= "pending"
                else:
                    possible_win= item.possibleWin
                
                print(f"analys of stake status hs been done and the value of the stakeStatus has been set to {status_value}")
                
                data = StakeObject(
                    stakeId=item.id,
                    home=item.home,
                    away=item.away,
                    stakeAmount=item.amount,
                    stakeStatus=status_value,
                    stakeResult=result,
                    date=item.created_at.isoformat(),
                    possibleWin= possible_win,
                    placement= item.invited_user_placement,
                )

                print(f"stake data to be sent is {data.stakeAmount, data.away, data.home, data.stakeAmount, data.stakeResult, data.stakeStatus, data.date, data.stakeId}")

                general_stakes_object.stakeData.append(data)
        except Exception as e:
            logger.error(f'An error occurred in __process_stakes_data while processing guest stakes: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Error processing guest stake data: {str(e)}'
            )

        #before we return the data we will sort by the time of creation: created_at
        general_stakes_object.stakeData.sort(key=lambda x: x.date, reverse=True)
        
        general_stakes_object.status= str(status.HTTP_200_OK)
        general_stakes_object.message= "the user stakes data has been retreived succesfuly"

        return general_stakes_object
    except Exception as e:
        logger.error(f'an unexpected error occured: __proccess_stakes_data, {str(e)}', exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail= f'an unexpected error occured: __process_stakes_data, {str(e)} ')