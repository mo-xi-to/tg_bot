import asyncio
import logging
from aiogram import Dispatcher, Bot
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN
from app.handlers import router
import app.database.request as rq
from app.database.models import async_main, engine
from app.ai import generate_morning_report, generate_ai_reminder_text

async def daily_morning_notification(bot: Bot):
    users = await rq.get_all_users()
    for user in users:
        now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=user.timezone)
        if now.hour == 9 and now.minute == 0:
            tasks = await rq.get_tasks_for_day(user.id, now.date())
            report = await generate_morning_report(user.name, tasks)
            await bot.send_message(user.tg_id, report)

async def check_reminders(bot: Bot):
    reminders = await rq.get_pending_reminders()
    if not reminders: 
        return
    
    for task, user in reminders:
        now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=user.timezone)
        if now >= task.deadline:
            try:
                text = await generate_ai_reminder_text(user.name, task.name, task.description)
                await bot.send_message(user.tg_id, text)
                await rq.add_history(user.id, "assistant", text)
                await rq.mark_as_reminded(task.id)
            except Exception as e:
                logging.error(f"Ошибка напоминания: {e}")

async def main():
    await async_main()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_morning_notification, 'interval', minutes=1, args=[bot])
    scheduler.add_job(check_reminders, 'interval', minutes=1, args=[bot])
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await engine.dispose()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())