#!/usr/bin/env python3
"""
Script to fix PostgreSQL sequence for prediction_market_trades table
Run this when you get duplicate key errors after manual data insertion
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

# Load environment
load_dotenv('.env')
load_dotenv('.env.prod', override=True)

DATABASE_URL = os.getenv('PROD_DATABASE_URL')

async def fix_sequence():
    """Reset the prediction_market_trades_id_seq to match current data"""
    
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        try:
            # Check current max ID
            result = await session.execute(text("SELECT MAX(id) FROM prediction_market_trades"))
            max_id = result.scalar()
            print(f"Current max ID in prediction_market_trades: {max_id}")
            
            # Check current sequence value
            result = await session.execute(text("SELECT nextval('prediction_market_trades_id_seq')"))
            next_seq = result.scalar()
            print(f"Next sequence value was: {next_seq}")
            
            # Reset sequence to max_id + 1
            if max_id is not None:
                new_seq_val = max_id + 1
                await session.execute(text(
                    f"SELECT setval('prediction_market_trades_id_seq', {new_seq_val}, false)"
                ))
                print(f"Reset sequence to: {new_seq_val}")
                
                # Verify the fix
                result = await session.execute(text("SELECT nextval('prediction_market_trades_id_seq')"))
                verify_seq = result.scalar()
                print(f"Verified next sequence value: {verify_seq}")
                
                await session.commit()
                print("✅ Sequence fixed successfully!")
            else:
                print("❌ No records found in prediction_market_trades table")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_sequence())
