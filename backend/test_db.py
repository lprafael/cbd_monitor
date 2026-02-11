import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

async def test_conn():
    load_dotenv()
    
    # CBD DB
    cbd_url = os.getenv('DATABASE_URL')
    if cbd_url:
        cbd_url = cbd_url.replace('postgresql://', 'postgresql+asyncpg://')
        print(f"Testing CBD DB: {cbd_url.split('@')[-1]}")
        try:
            engine = create_async_engine(cbd_url)
            async with engine.connect() as conn:
                print('CBD DB: OK')
        except Exception as e:
            print(f'CBD DB Error: {e}')
    
    # AUTH DB
    host = os.getenv("AUTH_DB_HOST")
    port = os.getenv("AUTH_DB_PORT")
    name = os.getenv("AUTH_DB_NAME")
    user = os.getenv("AUTH_DB_USER")
    pw = os.getenv("AUTH_DB_PASSWORD")
    
    auth_url = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{name}"
    print(f"Testing AUTH DB: {auth_url.split('@')[-1]}")
    try:
        engine_auth = create_async_engine(auth_url)
        async with engine_auth.connect() as conn:
            print('AUTH DB: OK')
    except Exception as e:
        print(f'AUTH DB Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_conn())
