from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
  pass

class User(Base):
  __tablename__ = 'users'

  id: Mapped[int] = mapped_column(primary_key=True)
  tg_id = mapped_column(BigInteger, unique=True)
  name: Mapped[str] = mapped_column(nullable=True)
  timezone: Mapped[int] = mapped_column()

  tasks = relationship('Task', back_populates='user', cascade='all, delete-orphan')

class Task(Base):
  __tablename__ = 'tasks'

  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(String(20))
  description: Mapped[str] = mapped_column(String(120))
  deadline: Mapped[datetime] = mapped_column()
  is_reminded: Mapped[bool] = mapped_column(default=False)

  user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

  user = relationship('User', back_populates='tasks')

class MessageHistory(Base):
  __tablename__ = 'history'

  id: Mapped[int] = mapped_column(primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
  role: Mapped[str] = mapped_column()
  content: Mapped[str] = mapped_column()
  timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

async def async_main():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)