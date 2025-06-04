# filepath: c:\dev-projects\dora_insight\backend\code\database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import text # For executing raw SQL like CREATE EXTENSION

# DATABASE_URL will be read from environment variable in a Docker setup
# For local development without Docker, you might want a default or to use .env here too
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://dorauser:dorapassword@localhost:5433/doradb")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncDBSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db_session():
    async with AsyncDBSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        # For pgvector, we need to ensure the extension is created in the database.
        # This is idempotent, so it's safe to run every time.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # await conn.run_sync(Base.metadata.drop_all) # <--- THIS LINE IS NOW COMMENTED OUT
        await conn.run_sync(Base.metadata.create_all)
        
        # Create unique index for user integrations if it doesn't exist
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_integration_unique 
            ON user_integrations(user_id, integration_type) 
            WHERE is_active = true
        """))