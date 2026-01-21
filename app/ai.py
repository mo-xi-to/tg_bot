import re
import os
import json
from openai import AsyncOpenAI
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from config import API_KEY
from app.logger import logger

class AI:
  MODEL = "xiaomi/mimo-v2-flash:free"
  BASE_URL = "https://openrouter.ai/api/v1"
    
  client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

  PROMPTS_DIR = "app/prompts"
    
  _prompts_cache: Dict[str, str] = {}

  @classmethod
  def _get_prompt(cls, filename: str) -> str:
        
    """Приватный метод для чтения промптов с кэшированием"""

    if filename not in cls._prompts_cache:
      path = os.path.join(cls.PROMPTS_DIR, filename)
            
      try:
        with open(path, 'r', encoding='utf-8') as f:
          cls._prompts_cache[filename] = f.read()
            
      except FileNotFoundError:
        logger.error(f"Файл промпта не найден: {path}")
        return ""
        
    return cls._prompts_cache.get(filename, "")

  @classmethod
  async def _ask_ai(cls, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
      
    """Единый внутренний метод для всех запросов к ИИ"""

    try:
      kwargs = {
        "model": cls.MODEL,
        "messages": messages,
      }
        
      if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

      completion = await cls.client.chat.completions.create(**kwargs)
        
      return completion.choices[0].message.content or ""
      
    except Exception as e:
      logger.error(f"Ошибка API OpenRouter: {e}")
      raise e

  @staticmethod
  def _parse_json(text: str) -> Dict[str, Any]:
        
    """Универсальный и безопасный парсер JSON из текста"""

    try:
      return json.loads(text)
      
    except json.JSONDecodeError:
      match = re.search(r'(\{.*\})', text, re.DOTALL)
        
      if match:
        try:
          return json.loads(match.group(1))
          
        except:
          pass
        
    return {"added_tasks": [], "deleted_tasks": [], "updated_tasks": [], "reply": text}

  @classmethod
  async def extract_tasks_from_ai(cls, prompt: str, tz_offset: int, tasks: List[Any], history: List[Any]) -> Dict[str, Any]:
      
    """Извлечение задач из текста"""

    tasks_str = "\n".join([f"- {t.name}" for t in tasks]) if tasks else "Пусто"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_str = (now + timedelta(hours=tz_offset)).strftime("%Y-%m-%d %H:%M:%S")

    template = cls._get_prompt('system_prompt.txt')
    system_instructions = template.format(
      current_time_str=time_str, 
      tasks_str=tasks_str
    )

    messages = [
      {"role": "system", "content": system_instructions},
    ]

    for msg in history:
      messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": prompt})

    raw_response = await cls._ask_ai(messages, json_mode=True)
    
    return cls._parse_json(raw_response)

  @classmethod
  async def generate_morning_report(cls, name: str, tasks: List[Any]) -> str:
    
    """Генерация утреннего дайджеста"""
    
    tasks_text = "\n".join([f"- {t.name} ({t.deadline.strftime('%H:%M')})" for t in tasks]) if tasks else "Планов нет."
        
    template = cls._get_prompt('morning_report.txt')
    prompt = template.format(name=name, tasks_text=tasks_text)

    return await cls._ask_ai([{"role": "user", "content": prompt}])

  @classmethod
  async def generate_ai_reminder_text(cls, name: str, tasks_data: str) -> str:
    
    """Генерация текста для напоминания"""
    
    template = cls._get_prompt('reminder.txt')
    prompt = template.format(user_name=name, tasks_data=tasks_data)

    return await cls._ask_ai([{"role": "user", "content": prompt}])