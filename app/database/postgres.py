from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()


class Postgres:
    async_engine: AsyncEngine

    @classmethod
    def connect_to_storage(cls) -> None:
        cls.async_engine = create_async_engine(settings.DB_URL, echo=settings.DEBUG)

    @classmethod
    def async_session_generator(cls) -> sessionmaker:
        return sessionmaker(cls.async_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def async_session(self) -> AsyncSession:
        async_session = self.async_session_generator()
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()


postgres = Postgres()
