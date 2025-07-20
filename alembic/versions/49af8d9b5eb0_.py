"""empty message

Revision ID: 49af8d9b5eb0
Revises: 07ccb2768bcc
Create Date: 2025-07-17 14:43:07.021253

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49af8d9b5eb0'
down_revision: Union[str, Sequence[str], None] = '07ccb2768bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create the enum type first
    trans_status_enum = sa.Enum('successfull', 'pending', 'failed', name='trans_status')
    trans_status_enum.create(op.get_bind(), checkfirst=True)

    # Add columns as nullable first
    op.add_column('transactions', sa.Column('status', trans_status_enum, nullable=True))
    op.add_column('transactions', sa.Column('merchant_request_id', sa.String(length=50), nullable=True))
    op.add_column('transactions', sa.Column('merchant_checkout_id', sa.String(length=50), nullable=True))
    op.add_column('transactions', sa.Column('receipt_number', sa.String(length=50), nullable=True))

    # Set default values for existing rows if needed
    op.execute("""
        UPDATE transactions 
        SET status = 'pending',
            merchant_request_id = 'N/A',
            merchant_checkout_id = 'N/A'
        WHERE merchant_request_id IS NULL
    """)

    # Now alter columns to be NOT NULL
    op.alter_column('transactions', 'status', nullable=False)
    op.alter_column('transactions', 'merchant_request_id', nullable=False)
    op.alter_column('transactions', 'merchant_checkout_id', nullable=False)

def downgrade() -> None:
    op.drop_column('transactions', 'receipt_number')
    op.drop_column('transactions', 'merchant_checkout_id')
    op.drop_column('transactions', 'merchant_request_id')
    op.drop_column('transactions', 'status')

    # Drop the enum type
    trans_status_enum = sa.Enum('successfull', 'pending', 'failed', name='trans_status')
    trans_status_enum.drop(op.get_bind(), checkfirst=True)