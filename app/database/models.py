from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=False)

async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
  """Базовый класс для всех моделей"""
  pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=True)
    timezone: Mapped[int] = mapped_column(default=0)

    tasks = relationship('Task', back_populates='user', cascade='all, delete-orphan')
    history = relationship('MessageHistory', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.tg_id}, name='{self.name}')>"

class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    is_reminded: Mapped[bool] = mapped_column(default=False, index=True)

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    
    user = relationship('User', back_populates='tasks')

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.name}', deadline='{self.deadline}')>"

class MessageHistory(Base):
    __tablename__ = 'history'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(1000))
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship('User', back_populates='history')

    def __repr__(self) -> str:
        return f"<History(user_id={self.user_id}, role='{self.role}')>"

async def async_main():
    
    """Инициализация таблиц базы данных"""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)