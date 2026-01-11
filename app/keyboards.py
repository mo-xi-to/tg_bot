from aiogram.utils.keyboard import InlineKeyboardBuilder

timezones = [i for i in range (2, 13)]

def inline_timezone():
  keyboard = InlineKeyboardBuilder()
  for timezone in timezones:
    keyboard.button(text=f'UTC +{timezone}', callback_data=f'tz_{timezone}')
  return keyboard.adjust(3).as_markup()