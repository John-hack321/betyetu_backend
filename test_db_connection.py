import asyncio
import os
from sqlalchemy import text
from db.db_setup import engine, Base, get_db

async def test_connection():
    try:
        async with engine.connect() as conn:
            print("✅ Successfully connected to the database!")
            # Test query
            result = await conn.execute(text("SELECT version();"))
            print("Database version:", result.scalar())
            
            # Check if tables exist
            result = await conn.run_sync(
                lambda sync_conn: sync_conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                )
            )
            tables = [row[0] for row in result.fetchall()]
            print("\nExisting tables:", tables or "No tables found")
            
    except Exception as e:
        print("❌ Failed to connect to the database:", str(e))
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
