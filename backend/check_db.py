import asyncio
import asyncpg
import sys

async def check():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/engineering_os')
        print("Successfully connected to database!")
        await conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check())
