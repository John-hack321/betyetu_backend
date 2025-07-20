from fastapi import status , HTTPException

async def update_balance(balance: int, amount: int, transaction_type: int):
    new_balance = 0
    if transaction_type == 1:  # deposit
        new_balance = balance + amount
    elif transaction_type == 2:  # withdrawal
        if amount > balance:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="balance is too low for withdrawal")
        new_balance = balance - amount
    return new_balance

