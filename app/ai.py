import re
import json
from openai import AsyncOpenAI
from datetime import datetime, timedelta, timezone

from config import API_KEY

client = AsyncOpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=API_KEY
)

async def extract_tasks_from_ai(prompt, user_timezone_offset, tasks_list, history_list):
  if tasks_list:
    tasks_info = []
    for t in tasks_list:
      time_str = t.deadline.strftime("%d.%m.%Y %H:%M")
      tasks_info.append(f"- {t.name} (Срок: {time_str}, Описание: {t.description or 'нет'})")
    tasks_str = "\n".join(tasks_info)
  else:
    tasks_str = "Список задач пуст."
    
  now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
  user_time = now_utc + timedelta(hours=user_timezone_offset)
  current_time_str = user_time.strftime("%Y-%m-%d %H:%M:%S")

  full_prompt = f"""Ты - умный ассистент по тайм-менеджменту. 
    Текущее время пользователя: {current_time_str}.
    
    СПИСОК ТЕКУЩИХ ЗАДАЧ:
    {tasks_str}
    
    Твоя задача: Проанализируй сообщение и ИСТОРИЮ чата и выдели ВСЕ действия. Пользователь может просить сделать несколько вещей сразу.
    ИНСТРУКЦИИ:
    1. ДОБАВЛЕНИЕ (added_tasks):  Список новых задач.
    2. УДАЛЕНИЕ (deleted_tasks): Список ТОЧНЫХ названий задач из списка выше, которые нужно удалить.
    3. ОБНОВЛЕНИЕ (updated_tasks): Список объектов, где "old_name" — точное имя из списка выше, а "new_data" - словарь с измененными полями.
    4. ПРОСМОТР: Формируй список задач в поле "reply" ТОЛЬКО если пользователь прямо попросил показать планы. Если просит задачи на конкретный день - выбери только их.
    5. ОБЩЕНИЕ И СОВЕТЫ: Если пользователь спрашивает совета по продуктивности или просто хочет обсудить свои планы - дай развернутый, мотивирующий 
      и полезный ответ в поле "reply". Ты должен быть экспертом в этой теме.
    6. ДУБЛИКАТЫ: Список названий задач, которые пользователь хочет добавить, но они УЖЕ есть в базе.
      Сравнивай каждую новую задачу со "СПИСКОМ ТЕКУЩИХ ЗАДАЧ". Если задача уже есть (даже если она написана другими словами, но смысл тот же), 
      НЕ добавляй её в "added_tasks". Просто скажи, что эта задача уже есть в списке.
    7. КОНТЕКСТНЫЕ ДОПОЛНЕНИЯ: Если пользователь пишет фразу (например: "и молоко", "а еще чай", "и хлеб"), это ЗНАЧИТ, что он 
      дополняет свою ПОСЛЕДНЮЮ созданную или обсуждаемую задачу. В этом случае КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО создавать новую задачу в 'added_tasks'.
      Ты должен использовать 'updated_tasks':
        1. "old_name": Точное имя задачи из списка выше (например, "Купить хлеб").
        2. "new_data": Новое объединенное имя (например, "Купить хлеб и молоко").

    Верни СТРОГО JSON:
    {{
      "added_tasks": [ {{ "name": "...", "description": "...", "deadline": "ГГГГ-ММ-ДД ЧЧ:ММ:СС" }} ],
      "deleted_tasks": ["Точное имя 1", "Точное имя 2"],
      "updated_tasks": [
        {{
          "old_name": "Точное имя из списка",
          "new_data": {{ "name": "новое имя", "description": "...", "deadline": "...", "is_reminded": false }}
        }}
      ],

      "reply": "ОБЯЗАТЕЛЬНО вежливый общий ответ о проделанной работе. Здесь используй эмодзи."
    }}
    
    Сообщение пользователя: "{prompt}" """

  messages = [{"role": "system", "content": full_prompt}]

  for msg in history_list:
    messages.append({"role": msg.role, "content": msg.content})
  
  messages.append({"role": "user", "content": prompt})

  completion = await client.chat.completions.create(
    model="meta-llama/llama-3.3-70b-instruct:free",
    messages=messages
  )
    
  raw_text = completion.choices[0].message.content
  match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
  return json.loads(match.group(1))

async def generate_morning_report(name, tasks_list):
  if tasks_list:
    for t in tasks_list:
      tasks_text = "\n".join([f"- {t.name} (в {t.deadline.strftime('%H:%M')})"])
  else:
    tasks_text = "Планов на сегодня нет."

  prompt = f"""
  Ты - заботливый личный ассистент по тайм-менеджменту. 
  Поприветствуй пользователя по имени {name}.
  Вот его задачи из базы данных на сегодня:
  {tasks_text}
    
  Твоя задача:
  1. Перечисли ТОЛЬКО те задачи, которые указаны выше. 
  2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО придумывать новые задачи, которых нет в списке.
  3. Если список пуст, просто пожелай хорошего отдыха.
  4. Если задачи есть, кратко напомни о них и пожелай удачи.
    
  Пиши кратко и по делу. Используй эмодзи.
  """
  completion = await client.chat.completions.create(
    model="meta-llama/llama-3.3-70b-instruct:free",
    messages=[{"role": "user", "content": prompt}]
  )
  return completion.choices[0].message.content
    
async def generate_ai_reminder_text(user_name, task_name, description):
  prompt = f"""
  Ты - заботливый личный ассистент. 
  Тебе нужно напомнить пользователю по имени {user_name} о задаче: "{task_name}".
  Дополнительное описание задачи: "{description or 'нет описания'}".
    
  Напиши короткое (1-2 предложения), дружелюбное и бодрое напоминание. 
  Используй эмодзи. Не будь слишком официальным.
  """
  completion = await client.chat.completions.create(
    model="meta-llama/llama-3.3-70b-instruct:free",
    messages=[{"role": "user", "content": prompt}]
  )
  return completion.choices[0].message.content