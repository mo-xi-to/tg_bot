from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class Keyboards:
  TZ_RANGE = range(2, 13)

  @staticmethod
  def inline_timezone() -> InlineKeyboardMarkup:
    
    """Генерирует сетку кнопок для выбора часового пояса"""

    builder = InlineKeyboardBuilder()

    for tz in Keyboards.TZ_RANGE:
      builder.button(
        text=f'UTC +{tz}',
        callback_data=f'tz_{tz}'
      )
    
    return builder.adjust(3).as_markup()
  
  @staticmethod
  def setting_menu() -> InlineKeyboardMarkup:
    
    """Генерирует меню настроек профиля"""

    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="👤 Изменить имя", callback_data="change_name"))
    builder.row(InlineKeyboardButton(text="🕒 Изменить часовой пояс", callback_data="change_tz"))

    return builder.as_markup()