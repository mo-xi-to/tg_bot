import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

import app.ai as ai
import app.keyboards as kb
import app.database.request as rq

router = Router()

class Reg(StatesGroup):
  name = State()
  timezone = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
  user = await rq.get_user(message.from_user.id)
  if user:
    await message.answer(f'Рад видеть тебя снова, {user.name}!')
  else:
    await state.set_state(Reg.name)
    await message.answer('Добро пожаловать! Введите ваше имя')

@router.message(Reg.name)
async def reg_step_two(message: Message, state: FSMContext):
  await state.update_data(name=message.text)
  await state.set_state(Reg.timezone)
  await message.answer('Выберите часовой пояс', reply_markup=kb.inline_timezone())

@router.callback_query(Reg.timezone)
async def reg_step_three(callback: CallbackQuery, state: FSMContext):
  tz = int(callback.data.split('_')[1])
  data = await state.get_data()
  
  await rq.add_user(tg_id=callback.from_user.id, name=data['name'], timezone=tz)
  await callback.message.answer('Регистрация завершена!')
  await state.clear()
  await callback.answer()

@router.message(F.text)
async def ai_chat(message: Message, state: FSMContext):
  user = await rq.get_user(message.from_user.id)
  await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')
    
  try:
    current_tasks = await rq.get_tasks(user.id)
    chat_history = await rq.get_history(user.id, limit=10)

    ai_data = await ai.extract_tasks_from_ai(message.text, user.timezone, current_tasks, chat_history)
    added = ai_data.get('added_tasks', [])
    deleted = ai_data.get('deleted_tasks', [])
    updated = ai_data.get('updated_tasks', [])
    reply = ai_data.get('reply')

    await rq.add_history(user.id, "user", message.text)

    for task in added:
      await rq.add_task(
        user_id=user.id,
        name=task.get('name', 'Без названия'),
        description=task.get('description', ''),
        deadline_str=task.get('deadline')
      )

    for task in deleted:
      await rq.delete_task(user.id, task)

    for task in updated:
      old_name = task.get('old_name')
      upd = task.get('new_data', {})
      if old_name:
        await rq.update_task(
          user_id=user.id,
          old_name=old_name,
          new_name=upd.get('name'),
          new_description=upd.get('description'),
          new_deadline_str=upd.get('deadline')
        )
    
    await rq.add_history(user.id, "assistant", reply)
    await message.answer(reply)

  except Exception as e:
    logging.error(f'Ошибка в ai_chat: {e}')
    await message.answer('Ошибка при обращении к ИИ')