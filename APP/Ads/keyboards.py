import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

set_ad_start = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Переслать сообщение 🔄", callback_data='set_ad_forward')],
    [InlineKeyboardButton(text="Добавить фото 🖼", callback_data='set_ad_photo')],
    [InlineKeyboardButton(text="Добавить текст ✍️", callback_data='set_ad_text')],
    [InlineKeyboardButton(text="Добавить стикер", callback_data='set_ad_sticker')],
    [InlineKeyboardButton(text="Добавить анимацию 🖼", callback_data='set_ad_animation')],
    [InlineKeyboardButton(text="Добавить callback клавиатуру", callback_data='set_ad_button_callback')]
])

set_ad = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить клавиатуру 🔗", callback_data='set_ad_button')],
    [InlineKeyboardButton(text="Добавить фото 🖼", callback_data='set_ad_photo')],
    [InlineKeyboardButton(text="Добавить анимацию 🖼", callback_data='set_ad_animation')],
    [InlineKeyboardButton(text="Добавить стикер", callback_data='set_ad_sticker')],
    [InlineKeyboardButton(text="Добавить callback клавиатуру", callback_data='set_ad_button_callback')],
    [InlineKeyboardButton(text="Добавить текст", callback_data='set_ad_text')],
    [InlineKeyboardButton(text="Добавить дату 🕘", callback_data='set_ad_date')],
    [InlineKeyboardButton(text="Завершить(Рассылка)", callback_data='set_ad_newsletter')],
    [InlineKeyboardButton(text="Завершить(В конце игры)", callback_data='set_ad_end')],
    [InlineKeyboardButton(text="Отмена 🚫", callback_data='set_ad_not')]
])  # установка рекламы


async def ad_button(markup_text: str):
    button_ad = InlineKeyboardBuilder()
    rows = markup_text.split('\n')
    
    for row in rows:
        row_buttons = []
        for button in row.split(' | '):
            parts = button.split(' - ')
            
            # Извлекаем текст или ставим невидимый символ \u200b
            text = parts[0].strip() if parts[0].strip() else "\u200b"
            
            # Умная проверка: если нет букв/цифр, оборачиваем в невидимые символы
            if not re.search(r'[a-zA-Zа-яА-ЯёЁ0-9]', text) and text != "\u200b":
                text = f"\u200b{text}\u200b"
                
            url = parts[1].strip() if len(parts) > 1 else ""
            style = parts[2].strip() if len(parts) > 2 else '0'
            custom_emoji_id = parts[3].strip() if len(parts) > 3 else 'None'
            
            kwargs = {'text': text, 'url': url}
            if style != '0':
                kwargs['style'] = style
            # Добавляем поддержку премиум эмодзи
            if custom_emoji_id != 'None':
                kwargs['icon_custom_emoji_id'] = custom_emoji_id
                
            row_buttons.append(InlineKeyboardButton(**kwargs))
            
        button_ad.row(*row_buttons)
        
    return button_ad.as_markup()


async def ad_button_callback(markup_text: str):
    button_ad = InlineKeyboardBuilder()
    rows = markup_text.split('\n')
    
    for row in rows:
        row_buttons = []
        for button in row.split(' | '):
            parts = button.split(' - ')
            
            text = parts[0].strip() if parts[0].strip() else "\u200b"
            
            if not re.search(r'[a-zA-Zа-яА-ЯёЁ0-9]', text) and text != "\u200b":
                text = f"\u200b{text}\u200b"
                
            callback_data = parts[1].strip() if len(parts) > 1 else 'None'
            style = parts[2].strip() if len(parts) > 2 else '0'
            custom_emoji_id = parts[3].strip() if len(parts) > 3 else 'None'
            
            kwargs = {'text': text, 'callback_data': callback_data}
            if style != '0':
                kwargs['style'] = style
            # Добавляем поддержку премиум эмодзи
            if custom_emoji_id != 'None':
                kwargs['icon_custom_emoji_id'] = custom_emoji_id
                
            row_buttons.append(InlineKeyboardButton(**kwargs))
            
        button_ad.row(*row_buttons)
        
    return button_ad.as_markup()
