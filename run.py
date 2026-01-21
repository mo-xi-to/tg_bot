import asyncio
from typing import List, Dict
from aiogram import Dispatcher, Bot
from aiogram.enums import ParseMode
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN
from app.ai import AI as ai
from app.logger import logger
from app.handlers import router
from app.database.request import Request as rq
from app.database.models import async_main, engine, User, Task

from config import MORNING_REPORT_HOUR, MORNING_REPORT_MINUTE

async def daily_morning_notification(bot: Bot) -> None:
    
    """Фоновая задача: отправка утреннего дайджеста задач в 9:00 по времени пользователя"""

    users: List[User] = await rq.get_all_users()

    for user in users:
        user_now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=user.timezone)

        if user_now.hour == MORNING_REPORT_HOUR and user_now.minute == MORNING_REPORT_MINUTE:
            try:
                tasks = await rq.get_tasks_for_day(user.id, user_now.date())
                report = await ai.generate_morning_report(user.name, tasks)

                await bot.send_message(user.tg_id, report, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Morning report sent to user {user.id}")

            except Exception as e:
                logger.error(f"Failed to send morning report to user {user.id}: {e}")

async def check_reminders(bot: Bot) -> None:
    
    """Фоновая задача: проверка дедлайнов и отправка групповых напоминаний черех ИИ"""

    reminders = await rq.get_pending_reminders()
    if not reminders:
        return
    
    user_task_map: Dict[int, List[Task]] = {}
    user_obj_map: Dict[int, User] = {}

    for task, user in reminders:
        user_now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=user.timezone)

        if user_now >= task.deadline:
            if user.id not in user_task_map:
                user_task_map[user.id] = []
                user_obj_map[user.id] = user
            
            user_task_map[user.id].append(task)

    for user_id, tasks in user_task_map.items():
        user = user_obj_map[user.id]

        task_summary = "\n".join([f"- {t.name}" + (f" ({t.description})" if t.description else "") for t in tasks])

        try:
            reminder_text = await ai.generate_ai_reminder_text(user.name, task_summary)

            await bot.send_message(user.tg_id, reminder_text, parse_mode=ParseMode.MARKDOWN)

            await rq.add_history(user.id, 'assistant', reminder_text)
            for task in tasks:
                await rq.mark_as_reminded(task.id)

            logger.info(f"Sent {len(tasks)} reminders to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending grouped reminders to user {user_id}: {e}")

async def main() -> None:
    
    """Инициализация систем и запуск бота"""

    logger.info("Starting TimeM Bot...")

    await async_main()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_morning_notification, 'interval', minutes=1, args=[bot])
    scheduler.add_job(check_reminders, 'interval', minutes=1, args=[bot])
    scheduler.start()
    logger.info("Scheduler started successfully")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    finally:
        logger.info("Shutting down...")
        scheduler.shutdown()
        await bot.session.close()
        await engine.dispose()
        logger.info("Connections closed. Bot stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    
    except (KeyboardInterrupt, SystemExit):
        pass
