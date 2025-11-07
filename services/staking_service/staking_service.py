import logging
from numbers import Number
import uuid
import sys

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from api.utils.util_accounts import get_account_data_by_user_id, increment_account_balance
from pydantic_schemas.stake_schemas import GuestStakeJoiningPayload, OwnerStakeInitiationPayload
from api.utils.util_stakes import create_stake_object, delete_stake_from_db_by_invite_code, get_stake_by_invite_code_from_db
from api.utils.util_accounts import subtract_stake_amount_from_db
from api.utils.util_stakes import add_guest_stake_data_to_db

logger = logging.getLogger(__name__)

class inviteCodeModel(BaseModel):
    statusCode: int
    inviteCode: str

class StakingService:
    def __init__(self, user_id: int):
        self.user_id= user_id

    # stake owner initiatin function
    async def owner_initiate_stake(self, db: AsyncSession, owner_stake_payload: OwnerStakeInitiationPayload)-> inviteCodeModel:
        account_balance_confirmed= await self.__confirm_account_balance(self.user_id, owner_stake_payload.stakeAmount, db)

        print(f"the accoutn balance has been confirmed and the boolean is {account_balance_confirmed}")
        if account_balance_confirmed:
            invite_code= await self.__generate_invite_code(self.user_id)
            print(f"the invite code has been generated for user  and its value is : {invite_code}")
            try:
                await self.__add_owner_stake_to_database(db, owner_stake_payload, self.user_id, invite_code)
                print(f"the stake owner data has been added ot the stake model in the db")
                await self.__update_account_balance_based_on_stake(db, self.user_id, owner_stake_payload.stakeAmount)
                print(f"the account balance has been updated to match the stake withdrawn ")

                invite_code_object= inviteCodeModel(
                    statusCode= status.HTTP_200_OK,
                    inviteCode=invite_code
                )
                
                print(f"the invite code {invite_code_object.inviteCode} has been sent to the frontend")

                return invite_code_object

            except Exception as e:
                logger.error(f'an error occured while adding stake onwer data to the database and updating account balance" {str(e)}',
                exc_info=True,
                extra={
                    "affected_user": self.user_id
                })

                raise HTTPException(
                    status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"an error occured while initating owner stake: {str(e)}"
                )

        else :

            logger.info(f"the user of user_id {self.user_id} account's balance cannot support the stake amount suggested ")

            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=f"the users account balance account balance cannot support the stake amount requested"
            )    

    async def join_initiated_stake(self, db: AsyncSession, guest_stake_data: GuestStakeJoiningPayload):
        # confirm if the account balance can accomodate the stake amount
        account_balance_confirmed= await self.__confirm_account_balance()
        if account_balance_confirmed:
            try:
                await self.__update_account_balance_based_on_stake(db, self.user_id, guest_stake_data.stakeAmount)
                await self.__add_guest_stake_data_to_database(db, self.user_id, guest_stake_data)

                return { # for now lets only return that we will find more to return later on
                    "status": status.HTTP_200_OK,
                    "message": "the user joined the stake succesfuly",
                }
            except Exception as e:
                logger.error(f'an error occured in the join initiated stake function {str(e)}')
        return {
            "status": status.HTTP_406_NOT_ACCEPTABLE,
            "detail": "the account balance cannot support the requested stake amount"
        }


    async def owner_cancel_stake(self, db: AsyncSession, invite_code: str):
        """
        will be used for deleting an already initiated stke when a user decides to cancel stake
        """
        # get stake from db 
        # refund money to owners accout balance , ensure to return this as part of return object
        try:
            db_stake_object= await get_stake_by_invite_code_from_db(db, invite_code)
            if not db_stake_object:
                logger.error(f"stake object returned from is undefined: owner_cancel_stake")

            db_account_object= await increment_account_balance(db, db_stake_object.amount, db_stake_object.user_id)
            if not db_account_object:
                logger.error(f"account object returned form database is undefined: owner_cancle_stake")
            
            await delete_stake_from_db_by_invite_code(db, invite_code)

            # i think by now we will have deleted the stake and more will be clear

            return {
                "statusCode": status.HTTP_200_OK,
                "message": "stake has been cancelled successfuly"
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"an error occured while cancelling owner stake: {str(e)}",
            exc_info=True,
            extra={
                "invite_code": invite_code
            })

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"an error occcured while cancelling stake onwer stake: {str(e)}"
            )


    # utilit functions for initiating stakes
    """
    checks is the account balance can handle the staking request amount
    get user account data , compares the account balance , and returns either true or false
    and the balance must be bigger or equal to the proposed amount or else the 
    proposal is rejected
    """
    async def __confirm_account_balance(self, user_id: int, onwer_stake_amount: int, db: AsyncSession):
        db_user_account_data= await get_account_data_by_user_id(user_id, db)
        print(f"the user account balance has been fetched and the balance is {db_user_account_data.balance}")

        if not db_user_account_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'an error occured while fetching user account data from the database')
        if onwer_stake_amount >= db_user_account_data.balance:
            return False
        return True

    # adds the stake initiator data to the datbase
    async def __add_owner_stake_to_database(self, db: AsyncSession, stake_data: OwnerStakeInitiationPayload, user_id: int, invite_code: str):
        db_stake_data= await create_stake_object(db, stake_data, user_id, invite_code)
        if not db_stake_data:
            logger.error(f'stake data returned from the db is not as defined')

    """
    for this we will make use of the uuid concept in python 
    """
    async def __generate_invite_code(self, user_id: int):
        try:
            uuid_string= str(uuid.uuid4()).replace('-','').upper()[:8]
            invite_code= f"{uuid_string[:4]}-{uuid_string[4:]}"
            print(f"the invite code has been generated and is {invite_code}")
            return invite_code
        except Exception as e:
            logger.error(f'an unexpecte error occured: __generate_invite_code: detail: {str(e)}', exc_info=True)
            raise RuntimeError(f'an unexpected error occured: __generate_invite_code {str(e)}')

    # dedcucts the stake amount from the wallet of the user
    async def __update_account_balance_based_on_stake(self, db: AsyncSession, user_id: int, stake_amount: int):
        db_account_data= await subtract_stake_amount_from_db(db, user_id, stake_amount)
        if not db_account_data:
            logger.error(f'an error occured while updating account data with the stake withdrawal data')

    # on the guest completing his stake or accepting his stake, this addd the guest's stake data to the database
    async def __add_guest_stake_data_to_database(self, db: AsyncSession, user_id: int, guest_stake_data: GuestStakeJoiningPayload):
        db_object= await add_guest_stake_data_to_db(db,user_id,guest_stake_data)
        if not db_object:
            logger.error(f'an error occured:__add_guest_stake_data , object returned from database is not as expected')