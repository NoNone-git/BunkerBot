from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from APP.Game.requests import players
from config import bot_username


async def invite_bot_link(room_id):
    chat_game_start = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Присоединиться", url=f'https://t.me/{bot_username}?start={room_id}')
    ]])
    return chat_game_start


async def stop_game(room_id, stop_count):
    stop_game_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"Остановить игру [{stop_count}/3]", callback_data=f'stop_{room_id}')
    ]])
    return stop_game_markup


async def group_voice_for_player_yes_or_no(user_id, not_votes):
    voice_for_player = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да ✅", callback_data=f'GrYesVoice_{user_id}_{not_votes}')],
        [InlineKeyboardButton(text="Нет, выбрать другого ❌", callback_data=f'GrVoice_{not_votes}')]
    ])
    return voice_for_player


async def group_player_voice(room_id, user_id, not_votes):
    select_players = InlineKeyboardBuilder()
    users = await players(room_id, user_id)
    
    for user in users:
        select_players.add(InlineKeyboardButton(
            text=f'[{user[2]}] {user[1]}',
            callback_data=f'GroupVoice_{user[0]}_{not_votes}'
        ))
        
    if int(not_votes) == 0:
        select_players.add(InlineKeyboardButton(
            text='[🚫] Скип [🚫]',
            callback_data=f'GroupVoice_skip_{not_votes}'
        ))
        
    return select_players.adjust(2).as_markup()


back_game_info = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад ↩", callback_data='game_info')]
])


async def play_info(card):
    # Оптимизированное построение клавиатуры без дублирования кода
    keyboard = [
        [InlineKeyboardButton(text="Случайные события", callback_data='events')],
        [InlineKeyboardButton(text="О катастрофе", callback_data='cataclysm'),
         InlineKeyboardButton(text="О бункере", callback_data='bunker_info')]
    ]
    
    if card is not None:
        parts = card.split('_')
        if len(parts) >= 2 and parts[-2] != 'card5':
            keyboard.append([
                InlineKeyboardButton(text=parts[0], callback_data=f'{parts[-2]}_{parts[-1]}'),
                InlineKeyboardButton(text='Купить карту №2', callback_data='PCard')
            ])
        else:
            keyboard.append([InlineKeyboardButton(text='Купить карту №2', callback_data='PCard')])
    else:
        keyboard.append([InlineKeyboardButton(text='Купить карту №2', callback_data='PCard')])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def use_card(room_id, user_id, name_card, char, pcard):
    select_players = InlineKeyboardBuilder()
    users = await players(room_id, user_id)
    
    for user in users:
        select_players.add(InlineKeyboardButton(
            text=f'[{user[2]}] {user[1]}',
            callback_data=f'Card_{name_card}_{user[0]}_{char}_{pcard}'
        ))
        
    select_players.add(InlineKeyboardButton(text="Назад ↩", callback_data='game_info'))
    return select_players.adjust(2).as_markup()


async def use_4_card(room_id, user_id, name_card, char, user_info, pcard):
    select_players = InlineKeyboardBuilder()
    users = await players(room_id, user_id)
    
    for user in users:
        select_players.add(InlineKeyboardButton(
            text=f'[{user[2]}] {user[1]}',
            callback_data=f'Card_{name_card}_{user[0]}_{char}_{pcard}'
        ))
        
    select_players.add(InlineKeyboardButton(
        text=f'[{user_info[1]}] {user_info[2]}',
        callback_data=f'Card_{name_card}_{user_info[3]}_{char}_{pcard}'
    ))
    select_players.add(InlineKeyboardButton(text="Назад ↩", callback_data='game_info'))
    
    return select_players.adjust(2).as_markup()


async def use_3_card(char_info, char, pcard):
    button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣", callback_data=f'Use3_{char_info[0][0]}_{char}_{pcard}'),
         InlineKeyboardButton(text="2️⃣", callback_data=f'Use3_{char_info[1][0]}_{char}_{pcard}')],
        [InlineKeyboardButton(text="3️⃣", callback_data=f'Use3_{char_info[2][0]}_{char}_{pcard}')]
    ])
    return button


pcard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1️⃣", callback_data='PCardUse_1'),
     InlineKeyboardButton(text="2️⃣", callback_data='PCardUse_2')],
    [InlineKeyboardButton(text="3️⃣", callback_data='PCardUse_3'),
     InlineKeyboardButton(text="4️⃣", callback_data='PCardUse_4')],
    [InlineKeyboardButton(text="Отмена 🚫", callback_data='game_info')]
])

pcard_1 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Заменить ✅", callback_data='UsePCard1'),
     InlineKeyboardButton(text="Отмена 🚫", callback_data='game_info')]
])

pcard_4 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🫀 Здоровье", callback_data='UsePCard4_health')],
    [InlineKeyboardButton(text="💊 Зависимость", callback_data='UsePCard4_addiction')],
    [InlineKeyboardButton(text="🕷 Фобия", callback_data='UsePCard4_phobia')],
    [InlineKeyboardButton(text="Отмена 🚫", callback_data='game_info')]
])


async def pcard_23(list1, card_info):
    characteristics_open = InlineKeyboardBuilder()
    for characteristics in list1:
        parts = characteristics.split('_')
        if len(parts) >= 3:
            characteristics_open.add(InlineKeyboardButton(
                text=parts[-3],
                callback_data=f'UsePCard{card_info}_{parts[-2]}'
            ))
            
    characteristics_open.add(InlineKeyboardButton(text="Отмена 🚫", callback_data='game_info'))
    return characteristics_open.adjust(2).as_markup()


chat_game = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="Перейти к боту", url=f'https://t.me/{bot_username}?')
]])


async def open_characteristics_group(list1):
    characteristics_open = InlineKeyboardBuilder()
    for characteristics in list1:
        parts = characteristics.split('_')
        if len(parts) >= 2:
            characteristics_open.add(InlineKeyboardButton(
                text=parts[0],
                callback_data=f'GrOpen_{parts[-2]}'
            ))
            
    return characteristics_open.adjust(2).as_markup()


bot_open_characteristics = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="Открыть характеристику", callback_data='BotOpen')
]])


async def link_chat(chat_id, msg):
    chat_str = str(chat_id)
    # Безопасное формирование ссылки
    if chat_str.startswith('-100'):
        chat_link = f'https://t.me/c/{chat_str[4:]}/{msg}'
    else:
        chat_link = f'https://t.me/c/{chat_str[1:]}/{msg}'
        
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Перейти в чат", url=chat_link)
    ]])


async def stop_discussion(number, max_number, room_id, admin):
    if admin != 'Admins':
        btn = InlineKeyboardButton(
            text=f"Завершить обсуждение [{number}/{max_number}]", 
            callback_data=f'StopD_{number}_{max_number}_{room_id}'
        )
    else:
        btn = InlineKeyboardButton(
            text="Завершить обсуждение", 
            callback_data=f'AdmStopD_{room_id}'
        )
        
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


async def next_round(number_dis, max_number, room_id, number_next, admin_next, admin_dis):
    btn_dis = (
        InlineKeyboardButton(text=f"Начать голосование [{number_dis}/{max_number}]", callback_data=f'StopD_{number_dis}_{max_number}_{room_id}_{number_next}')
        if admin_dis != 'Admins' else
        InlineKeyboardButton(text="Начать голосование", callback_data=f'AdmStopD_{room_id}')
    )
    
    btn_next = (
        InlineKeyboardButton(text=f"Начать новый раунд [{number_next}/{max_number}]", callback_data=f'NextR_{number_next}_{max_number}_{room_id}_{number_dis}')
        if admin_next != 'Admins' else
        InlineKeyboardButton(text="Начать новый раунд", callback_data=f'AdmNextR_{room_id}')
    )
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_dis],
        [btn_next]
    ])


bot_link_votes = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="Голосовать 🗳", url=f'https://t.me/{bot_username}?')
]])