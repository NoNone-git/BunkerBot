from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import bot_username, query
from APP.BaseFunc.settings import Settings
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

# === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ===
# Вынесено из функции rights_settings для оптимизации памяти
RIGHTS_TEXT_DICT = {
    'Votes': 'Голосованием', 
    'Admins': 'Админы', 
    'StartPlayer': 'Запустивший',
    'Players': 'Игроки', 
    'Users': 'Все'
}


async def bot_commands(bot: Bot):
    group_commands = [
        BotCommand(command='settings', description='Настройки чата'),
        BotCommand(command='game', description='Запустить регистрацию'),
        BotCommand(command='start', description='Старт игры'),
        BotCommand(command='extend_register', description='Продлить регистрацию'),
        BotCommand(command='extend', description='Отключить таймер регистрации'),
        BotCommand(command='stop_register', description='Отменить регистрацию'),
        BotCommand(command='extend_discussion', description='Продлить обсуждение'),
        BotCommand(command='stop_game', description='Завершить игру'),
    ]
    private_commands = [
        BotCommand(command='bonus', description='🪙 Получить бонус'),
        BotCommand(command='start', description='🚀 Запустить бота'),
        BotCommand(command='settings', description='⚙️ Настройки чата'),
        BotCommand(command='gift', description='🎁 Премиум в подарок'),
        BotCommand(command='ref_url', description='🤝 Реферальная ссылка')
    ]
    await bot.set_my_commands(commands=group_commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(commands=private_commands, scope=BotCommandScopeAllPrivateChats())


markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Правила игры 📕", callback_data='rules1')],
    [InlineKeyboardButton(text="Войти в группу 🔗", url='https://t.me/chatBunkerGame')],
    [InlineKeyboardButton(
        text="Добавить бота в группу ➕",
        url=f'https://t.me/{bot_username}?startgroup=add-GroupBunkerbot&admin=delete_messages+pin_messages')],
    [InlineKeyboardButton(text="📊 Моя статистика", callback_data='my_statistics'),
     InlineKeyboardButton(text="Топ-10 игроков 🏆", callback_data='leaders')],
    [InlineKeyboardButton(text="Канал бота. Обновления 📰", url='https://t.me/bunkerbotchat')],
])  # меню бота

chat = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Присоединиться к чату ➕", url='https://t.me/chatBunkerGame')]
])

projects = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Викторины", url='https://t.me/ViktorinaOnlineBot/start')],
    [InlineKeyboardButton(text="Назад ↩", callback_data='check')]
])

send_votes_info = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад к правилам ↩", callback_data='rules1')]
])

rules_markup1 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡️", callback_data='rules2')],
    [InlineKeyboardButton(text="В меню ↩", callback_data='check')],
    [InlineKeyboardButton(text="Как работает голосование🧐", callback_data='votes_info_in_play')]
])

invite = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пригласить друга 🎁", callback_data='invite')]
])

channel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Перейти в канал 🎁", callback_data='invite', url='https://t.me/bunkerbotchat')]
])

rules_markup2 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️", callback_data='rules1'),
     InlineKeyboardButton(text="➡️", callback_data='rules3')],
    [InlineKeyboardButton(text="В меню ↩", callback_data='check')],
    [InlineKeyboardButton(text="Как работает голосование🧐", callback_data='votes_info_in_play')]
])

rules_markup3 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️", callback_data='rules2')],
    [InlineKeyboardButton(text="В меню ↩", callback_data='check')],
    [InlineKeyboardButton(text="Как работает голосование🧐", callback_data='votes_info_in_play')]
])


# === ОПТИМИЗИРОВАННЫЕ ПАРСЕРЫ КНОПОК ===

async def ad_button_callback(markup_text: str):
    button_ad = InlineKeyboardBuilder()
    rows = markup_text.split('\n')
    
    for row in rows:
        row_buttons = []
        for button in row.split(' | '):
            parts = button.split(' - ')
            text = parts[0]
            callback_data = parts[1] if len(parts) > 1 else 'None'
            
            row_buttons.append(InlineKeyboardButton(text=text, callback_data=callback_data))
            
        button_ad.row(*row_buttons)
        
    return button_ad.as_markup()


async def ad_button(markup_text: str):
    button_ad = InlineKeyboardBuilder()
    rows = markup_text.split('\n')
    
    for row in rows:
        row_buttons = []
        for button in row.split(' | '):
            parts = button.split(' - ')
            text = parts[0]
            url = parts[1] if len(parts) > 1 else ""
            
            row_buttons.append(InlineKeyboardButton(text=text, url=url))
            
        button_ad.row(*row_buttons)
        
    return button_ad.as_markup()

# =======================================


back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню ↩", callback_data='check')]])


async def all_settings(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳", callback_data=f'timer_settings_{chat_id}'),
         InlineKeyboardButton(text="🪪", callback_data=f'rights_settings_{chat_id}'),
         InlineKeyboardButton(text="🖼", callback_data=f'game_settings_{chat_id}')],
        [InlineKeyboardButton(text="💎 Характеристики 💎", callback_data=f'prem_settings_{chat_id}')]
    ])


async def game_settings(settings: Settings, chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1️⃣ [{'🟢' if settings.pin_votes_msg else '🔴'}]",
                              callback_data=f'GS+pin_votes_msg+{chat_id}'),
         InlineKeyboardButton(text=f"2️⃣ [{'🟢' if settings.pin_open_char else '🔴'}]",
                              callback_data=f'GS+pin_open_char+{chat_id}')],
        [InlineKeyboardButton(text=f"3️⃣ [{'🟢' if settings.anonymous_votes else '🔴'}]",
                              callback_data=f'GS+anonymous_votes+{chat_id}'),
         InlineKeyboardButton(text=f"4️⃣ [{'🟢' if settings.delete_messages else '🔴'}]",
                              callback_data=f'GS+delete_messages+{chat_id}')],
        [InlineKeyboardButton(text=f"5️⃣ [{'🟢' if settings.delete_round_msgs else '🔴'}]",
                              callback_data=f'GS+delete_round_msgs+{chat_id}'),
         InlineKeyboardButton(text=f"6️⃣ [{'🟢' if settings.pin_info_game_msg else '🔴'}]",
                              callback_data=f'GS+pin_info_game_msg+{chat_id}')],
        [InlineKeyboardButton(text=f"7️⃣ [{'🟢' if settings.pin_reg_msg else '🔴'}]",
                              callback_data=f'GS+pin_reg_msg+{chat_id}')],
        [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
    ])


async def back_settings(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
    ])


async def rights_settings(settings: Settings, chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1️⃣ [{RIGHTS_TEXT_DICT[str(settings.start_game)]}]",
                              callback_data=f'RS+1+{chat_id}'),
         InlineKeyboardButton(text=f"2️⃣ [{RIGHTS_TEXT_DICT[str(settings.stop_game)]}]",
                              callback_data=f'RS+2+{chat_id}')],
        [InlineKeyboardButton(text=f"3️⃣ [{RIGHTS_TEXT_DICT[str(settings.stop_register)]}]",
                              callback_data=f'RS+3+{chat_id}'),
         InlineKeyboardButton(text=f"4️⃣ [{RIGHTS_TEXT_DICT[str(settings.stop_discussion)]}]",
                              callback_data=f'RS+4+{chat_id}')],
        [InlineKeyboardButton(text=f"5️⃣ [{RIGHTS_TEXT_DICT[str(settings.next_round)]}]",
                              callback_data=f'RS+5+{chat_id}'),
         InlineKeyboardButton(text=f"6️⃣ [{RIGHTS_TEXT_DICT[str(settings.extend_register)]}]",
                              callback_data=f'RS+6+{chat_id}')],
        [InlineKeyboardButton(text=f"7️⃣ [{RIGHTS_TEXT_DICT[str(settings.extend_discussion)]}]",
                              callback_data=f'RS+7+{chat_id}')],
        [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
    ])


channel_link = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Новости и обновления 📰", url='https://t.me/bunkerbotchat')]
])

chat_game = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Перейти к боту", url=f'https://t.me/{bot_username}?')]
])


async def sql_query(type_query):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ДА", callback_data=f'{query}_{type_query}'),
         InlineKeyboardButton(text="ОТМЕНА", callback_data='sqlNo')]
    ])


async def my_list(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼", callback_data='mylist+profession'),
         InlineKeyboardButton(text="👤", callback_data='mylist+gender'),
         InlineKeyboardButton(text="✳", callback_data='mylist+fact')],
        [InlineKeyboardButton(text="🧩", callback_data='mylist+hobbies'),
         InlineKeyboardButton(text="🎒", callback_data='mylist+baggage'),
         InlineKeyboardButton(text="🫀", callback_data='mylist+health')],
        [InlineKeyboardButton(text="🕷", callback_data='mylist+phobia'),
         InlineKeyboardButton(text="💊", callback_data='mylist+addiction'),
         InlineKeyboardButton(text="😎", callback_data='mylist+persona')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def my_bunker_list(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠", callback_data='mylist+bunker_rooms'),
         InlineKeyboardButton(text="🧳", callback_data='mylist+supplies'),
         InlineKeyboardButton(text="🏞", callback_data='mylist+location_bunker')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def my_cataclysm_list(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def yes_char_set(type_char, chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Установить", callback_data=f'charset+{type_char}'),
         InlineKeyboardButton(text="Отмена 🔙", callback_data=f'prem_settings_{chat_id}')]
    ])


async def del_all_cataclysm(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Да, очистить", callback_data=f'del_cataclysms_{chat_id}'),
         InlineKeyboardButton(text="Отмена 🔙", callback_data=f'prem_settings_{chat_id}')]
    ])


bonus = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔗 Подписаться", url='https://t.me/bunkerbotchat')],
    [InlineKeyboardButton(text="☑️ Проверить", callback_data='check_bonus')]
])


async def back_set_lists(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Другие характеристики 🎭", callback_data=f'prem_char_{chat_id}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def prem_settings(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭", callback_data=f'prem_char_{chat_id}'),
         InlineKeyboardButton(text="🏠", callback_data=f'prem_bunker_{chat_id}'),
         InlineKeyboardButton(text="💣", callback_data=f'prem_cataclysm_{chat_id}')],
        [InlineKeyboardButton(text="🤖 Формат ИИ-концовки", callback_data=f'prem_ai_{chat_id}')],
        [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
    ])


async def prem_ai_settings(chat_id, ai_format):
    btn_text = "🟢 Длинный рассказ" if ai_format == 0 else "🟢 Короткий прогноз"
    toggle_val = 1 if ai_format == 0 else 0
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=f'UpdateAIFormat_{chat_id}_{toggle_val}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def set_lists(char_type, chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Установить", callback_data=f'SetMylist+{char_type}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def cataclysm_set(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Установить", callback_data=f'set_cataclysm_{chat_id}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def update_lists(char_type, chat_id, settings_value):
    status_text = "🔴 Отключить" if settings_value else "🟢 Подключить"
    status_action = 'off' if settings_value else 'on'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♻️ Поменять", callback_data=f'SetMylist+{char_type}')],
        [InlineKeyboardButton(text=status_text, callback_data=f'UpdateStatusChar+{char_type}+{status_action}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def off_set(type_char, chat_id, settings_value):
    status_text = "🔴 Отключить" if settings_value else "🟢 Подключить"
    status_action = 'off' if settings_value else 'on'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=status_text, callback_data=f'UpdateStatusChar+{type_char}+{status_action}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def set_cataclysm(chat_id, settings_value):
    status_text = "🔴 Отключить" if settings_value else "🟢 Подключить"
    status_action = 'off' if settings_value else 'on'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data=f'set_cataclysm_{chat_id}'),
         InlineKeyboardButton(text="➖ Удалить", callback_data=f'delete_cataclysm_{chat_id}')],
        [InlineKeyboardButton(text=status_text, callback_data=f'UpdateStatusCataclysm+cataclysm+{status_action}')],
        [InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id}')]
    ])


async def add_cataclysm(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Добавить", callback_data=f'add_cataclysm_{chat_id}'),
         InlineKeyboardButton(text="Отмена 🔙", callback_data=f'prem_settings_{chat_id}')]
    ])


async def delete_cataclysm(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☑️ Очистить", callback_data=f'dellAll_cataclysm_{chat_id}'),
         InlineKeyboardButton(text="Отмена 🔙", callback_data=f'prem_cataclysm_{chat_id}')]
    ])