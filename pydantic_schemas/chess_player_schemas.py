from pydantic import BaseModel

import enum

# enums to support some data types
class country_code(enum.IntEnum):
    KE = 254

class account_status_code(enum.IntEnum):
    basic = 1

class ChessProfileBase(BaseModel):
    chess_username : str

class CreateChessDbProfile(ChessProfileBase): # this is for adding a new chess profile to the database
    user_id : int
    player_id : int
    followers : int
    country : country_code
    account_status : account_status_code
    account_verification_status : bool
    league : str

class UserDataReturnType(CreateChessDbProfile):
    ...

class ChessProfileSchema(BaseModel):
    ...