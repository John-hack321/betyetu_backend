from fastapi import status , HTTPException
from pydantic_schemas.transaction_schemas import trans_type

async def update_balance(balance: int, amount: int, transaction_type: trans_type):
    new_balance = 0
    if transaction_type == trans_type.deposit:  # deposit
        new_balance = balance + amount
    elif transaction_type == trans_type.withdrawal:  # withdrawal
        if amount > balance or amount < 10 :
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="balance is too low for withdrawal")
        new_balance = balance - amount
    return new_balance

