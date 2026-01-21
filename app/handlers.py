from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from app.ai import AI as ai
from app.logger import logger
from config import ERROR_STICKER_ID
from app.keyboards import Keyboards as kb
from app.database.request import Request as rq

router = Router()

class Reg(StatesGroup):

  """Состояния для регистрации и изменения настроек"""

  name = State()
  timezone = State()

async def process_ai_actions(user_id: int, ai_data: dict) -> None:

  """Обрабатывает изменения в БД (задачи и профиль), присланные ИИ"""

  for task in ai_data.get('added_tasks', []):
      await rq.add_task(
        user_id=user_id,
        name=task.get('name', 'Без названия'),
        description=task.get('description', ''),
        deadline_str=task.get('deadline')
      )

  for task_name in ai_data.get('deleted_tasks', []):
    await rq.delete_task(user_id, task_name)

  for item in ai_data.get('updated_tasks', []):
    old_name = item.get('old_name')
    new_data = item.get('new_data', {})
      
    if old_name:
      await rq.update_task(
        user_id=user_id,
        old_name=old_name,
        new_name=new_data.get('name'),
        new_description=new_data.get('description'),
        new_deadline_str=new_data.get('deadline')
      )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
  
  """Обработка команды /start"""

  await state.clear()
  user = await rq.get_user(message.from_user.id)

  if user:
    await message.answer(
      f"Рад видеть тебя снова, {user.name}!",
      reply_markup=ReplyKeyboardRemove()
    )

  else:
    await state.set_state(Reg.name)
    await message.answer(
      "Добро пожаловать! Я твой ИИ-помощник. \nВведите ваше имя для регистрации:",
      reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command('settings'))
async def cmd_settings(message: Message) -> None:
  
  """Меню настроек профиля"""

  await message.answer(
    "⚙️ **Настройки профиля**\nВыберите, что вы хотите изменить:",
    reply_markup=kb.setting_menu()
  )

@router.message(Command('tasks'))
async def cmd_tasks(message: Message) -> None:
  
  """Быстрый просмотр всех задач (без ИИ)"""

  user = await rq.get_user(message.from_user.id)
  if not user: 
    return
  
  tasks = await rq.get_tasks(user.id)
  if not tasks:
    await message.answer("У вас пока нет активных задач.")
    return
  
  text = "📋 **Ваши текущие задачи:**\n\n"
  for i, t in enumerate(tasks, 1):
    text += f"{i}. {t.name}\n   ⏰ {t.deadline.strftime('%d.%m %H:%M')}\n"

  await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(Reg.name)
async def reg_name_input(message: Message, state: FSMContext) -> None:

  """Прием имени (регистрация или смена)"""

  user = await rq.get_user(message.from_user.id)

  if user:
    await rq.update_user_profile(tg_id=message.from_user.id, name=message.text)
    await message.answer(f"✅ Имя успешно изменено на: **{message.text}**", parse_mode=ParseMode.MARKDOWN)
    await state.clear()

  else:
    await state.update_data(name=message.text)
    await state.set_state(Reg.timezone)
    await message.answer(f"Приятно познакомиться, {message.text}! Теперь выберите часовой пояс:", reply_markup=kb.inline_timezone())

@router.callback_query(Reg.timezone)
async def reg_timezone_input(callback: CallbackQuery, state: FSMContext) -> None:

  """Приём часового пояса (регистрация или смена)"""

  tz = int(callback.data.split('_')[1])
  user = await rq.get_user(callback.from_user.id)

  if user:
    await rq.update_user_profile(tg_id=callback.from_user.id, timezone=tz)
    await callback.message.answer(f"✅ Часовой пояс изменен на: **UTC +{tz}**")

  else:
    data = await state.get_data()

    await rq.add_user(tg_id=callback.from_user.id, name=data['name'], timezone=tz)
    await callback.message.answer("✨ Регистрация завершена! Просто пишите мне свои задачи.")

  await state.clear()
  await callback.answer()

@router.callback_query(F.data == "change_name")
async def cb_change_name(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(Reg.name)
  await callback.message.answer("Ведите ваше новое имя:")
  await callback.answer()

@router.callback_query(F.data == "change_tz")
async def cb_change_tz(callback: CallbackQuery, state: FSMContext) -> None:
  await state.set_state(Reg.timezone)
  await callback.message.answer("Выберите новый часовой пояс:", reply_markup=kb.inline_timezone())
  await callback.answer()

@router.message(F.text)
async def handle_ai_chat(message: Message) -> None:
  
  """Обработка всех текстовых сообщений через ИИ"""

  user = await rq.get_user(message.from_user.id)

  if not user:
    await message.answer('Пожалуйста, сначала зарегистрируйтесь: /start')
    return
  
  await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')

  try:
    current_tasks = await rq.get_tasks(user.id)
    chat_history = await rq.get_history(user.id, limit=10)

    ai_data = await ai.extract_tasks_from_ai(message.text, user.timezone, current_tasks, chat_history)
    
    added = ai_data.get('added_tasks', [])
    deleted = ai_data.get('deleted_tasks', [])
    updated = ai_data.get('updated_tasks', [])
    profile = ai_data.get('update_profile')
    reply = ai_data.get('reply') or "Запрос обработан."

    logger.info(f"User {user.id} | A:{len(added)} D:{len(deleted)} U:{len(updated)}")

    await rq.add_history(user.id, "user", message.text)

    await process_ai_actions(user.id, ai_data)

    if profile:
      new_name = profile.get('name')
      raw_tz = profile.get('timezone')

      if new_name or raw_tz is not None:
        try:
          new_tz = int(raw_tz) if raw_tz is not None else None
          await rq.update_user_profile(user.tg_id, name=new_name, timezone=new_tz)
          logger.info(f"User {user.id} updated profile via AI")
        
        except (ValueError, TypeError):
          logger.warning(f"ИИ прислал некорректный формат часового пояса: {raw_tz}")

    await rq.add_history(user.id, "assistant", reply)
    await message.answer(reply, parse_mode=ParseMode.MARKDOWN)
  
  except Exception as e:
    logger.error(f'Ошибка в ai_chat для пользователя {message.from_user.id}: {e}', exc_info=True)
    await message.answer_sticker(sticker=ERROR_STICKER_ID)
    await message.answer('Упс! Что-то пошло не так. Попробуй еще раз чуть позже.')
