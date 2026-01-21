from datetime import datetime, time
from sqlalchemy import select, delete, update, and_, func
from app.database.models import async_session, User, Task, MessageHistory

class Request:
    # --- РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ---
    @staticmethod
    async def get_user(tg_id):
        async with async_session() as session:
            return await session.scalar(select(User).where(User.tg_id == tg_id))
    
    @staticmethod
    async def add_user(tg_id, name, timezone):
        async with async_session() as session:
            new_user = User(tg_id=tg_id, name=name, timezone=timezone)
            session.add(new_user)
            await session.commit()

    @staticmethod
    async def get_all_users():
        async with async_session() as session:
            result = await session.scalars(select(User))
            return result.all()

    # --- РАБОТА С ЗАДАЧАМИ ---
    @staticmethod
    async def get_tasks(user_id):
        async with async_session() as session:
            result = await session.scalars(select(Task).where(Task.user_id == user_id))
            return result.all()

    @staticmethod
    async def add_task(user_id, name, description, deadline_str):
        async with async_session() as session:
            deadline = datetime.fromisoformat(deadline_str)
            new_task = Task(name=name, description=description, deadline=deadline, user_id=user_id)
            session.add(new_task)
            await session.commit()

    @staticmethod
    async def delete_task(user_id, task_name):
        async with async_session() as session:
            statement = delete(Task).where(Task.user_id == user_id, Task.name == task_name)
            await session.execute(statement)
            await session.commit()

    @staticmethod
    async def update_task(user_id, old_name, new_name=None, new_description=None, new_deadline_str=None):
        async with async_session() as session:
            update_data = {}
            if new_name: update_data['name'] = new_name
            if new_description: update_data['description'] = new_description
            if new_deadline_str:
                update_data['deadline'] = datetime.fromisoformat(new_deadline_str)
                update_data['is_reminded'] = False

            if not update_data: return
            
            statement = update(Task).where(
                Task.user_id == user_id, 
                func.lower(Task.name) == func.lower(old_name) 
            ).values(**update_data)
            await session.execute(statement)
            await session.commit()

    @staticmethod
    async def get_tasks_for_day(user_id, date_to_check):
        async with async_session() as session:
            start_of_day = datetime.combine(date_to_check, time.min)
            end_of_day = datetime.combine(date_to_check, time.max)
            result = await session.scalars(
                select(Task).where(
                    and_(Task.user_id == user_id, Task.deadline >= start_of_day, Task.deadline <= end_of_day)
                )
            )
            return result.all()

    # --- НАПОМИНАНИЯ ---
    @staticmethod
    async def get_pending_reminders():
        async with async_session() as session:
            result = await session.execute(
                select(Task, User).join(User).where(Task.is_reminded == False)
            )
            return result.all()

    @staticmethod
    async def mark_as_reminded(task_id):
        async with async_session() as session:
            await session.execute(
                update(Task).where(Task.id == task_id).values(is_reminded=True)
            )
            await session.commit()

    # --- ИСТОРИЯ ЧАТА ---
    @staticmethod
    async def add_history(user_id, role, content):
        async with async_session() as session:
            session.add(MessageHistory(user_id=user_id, role=role, content=content))
            await session.commit()

    @staticmethod
    async def get_history(user_id, limit=10):
        async with async_session() as session:
            result = await session.scalars(
                select(MessageHistory).where(MessageHistory.user_id == user_id)
                .order_by(MessageHistory.timestamp.desc()).limit(limit)
            )
            messages = result.all()
            return messages[::-1]
        
    @staticmethod
    async def update_user_profile(tg_id, name=None, timezone=None):
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))

            if user:
                if name:
                    user.name = name
                
                if timezone is not None:
                    user.timezone = timezone
                
                await session.commit()
                return True
            
            return False