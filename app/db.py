from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None

def init_engine(db_url: str) -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    _engine = create_async_engine(db_url, echo=False, future=True)
    _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)
    return _sessionmaker

def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("DB sessionmaker init qilinmagan. init_engine() chaqiring!")
    return _sessionmaker

async def create_tables() -> None:
    from .models import User, Test, Question, Attempt, Answer  # noqa
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)