import html
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

import APP.Game.keyboards as kb
import APP.Game.requests as rq
from APP.Game.func import card_2, card_1, card_4, PlayerState
from APP.Game.Classes import Room
from config import user_state, rooms
from APP.Middlewares.decorators import retry_after_decorate
from APP.Middlewares.throttling_middleware import ThrottlingMiddleware, flag_default


router = Router()
router.callback_query.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                                      throttle_time_end=4, throttle_time_other=0.2,
                                                      throttle_time_card=4))
router.message.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                               throttle_time_end=4, throttle_time_other=0.2,
                                               throttle_time_card=4))

# === ГЛОБАЛЬНЫЙ СЛОВАРЬ ХАРАКТЕРИСТИК ===
# Заменяет огромные if-elif блоки в каждой функции
CHAR_NAMES_RU = {
    'gender': '👤 Био. информация',
    'profession': '💼 Профессия',
    'fact': '✳ Доп. информация',
    'hobbies': '🧩 Хобби',
    'baggage': '🎒 Багаж',
    'phobia': '🕷 Фобия',
    'addiction': '💊 Зависимость',
    'persona': '😎 Черта характера',
    'health': '🫀 Здоровье'
}


@router.callback_query(F.data.startswith('card1_'), PlayerState.in_game, flags=flag_default)
async def callback_use_card_1(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    card_info = await rq.get_player_card(callback.from_user.id)
    
    if not card_info.startswith('open_'):
        parts = callback.data.split('_')
        char_type = parts[1]
        result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
        
        data = await state.get_data()
        await retry_after_decorate(callback.message.edit_text)(
            text=f'<b><blockquote>🃏———<i><u>КАРТА ДЕЙСТВИЯ</u></i>———🃏</blockquote>\n\n'
                 f'Выберите игрока, с которым хотите поменяться картой: {result}</b>',
            parse_mode='HTML',
            reply_markup=await kb.use_card(data['chat_id'], callback.from_user.id,
                                           'card1', char_type, 0))


@router.callback_query(F.data.startswith('card2_'), PlayerState.in_game, flags=flag_default)
async def callback_use_card_2(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    card_info = await rq.get_player_card(callback.from_user.id)
    
    if not card_info.startswith('open_'):
        parts = callback.data.split('_')
        char_type = parts[1]
        result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
        
        data = await state.get_data()
        await retry_after_decorate(callback.message.edit_text)(
            text=f'<b><blockquote>🃏———<i><u>КАРТА ДЕЙСТВИЯ</u></i>———🃏</blockquote>\n\n'
                 f'Выберите, у какого игрока вы хотите подсмотреть карту: {result}</b>',
            parse_mode='HTML',
            reply_markup=await kb.use_card(data['chat_id'], callback.from_user.id,
                                           'card2', char_type, 0))


@router.callback_query(F.data.startswith('card3_'), PlayerState.in_game, flags=flag_default)
async def callback_use_card_3(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    card_info = await rq.get_player_card(callback.from_user.id)
    
    if not card_info.startswith('open_'):
        data = await state.get_data()
        room: Room = rooms[data['chat_id']]
        parts = callback.data.split('_')
        char_type = parts[1]
        
        result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
        
        if char_type == 'gender':
            msg_text = await rq.regeneration_gender_select(room, state)
        elif char_type == 'profession':
            msg_text = await rq.regeneration_profession_select(room, state, callback.from_user.id)
        else:
            msg_text = await rq.regeneration_characteristics_select(char_type, room)
            
        await retry_after_decorate(callback.message.edit_text)(
            text=f"<b><blockquote>🃏———<i><u>КАРТА ДЕЙСТВИЯ</u></i>———🃏</blockquote>\n\n"
                 f"Выберите новое значение карты {result}:\n\n"
                 f"<blockquote>1️⃣ {msg_text[0][1]}\n\n2️⃣ {msg_text[1][1]}\n\n"
                 f"3️⃣ {msg_text[2][1]}</blockquote></b>",
            parse_mode='HTML',
            reply_markup=await kb.use_3_card(msg_text, char_type, 0))


@router.callback_query(F.data.startswith('card4_'), PlayerState.in_game, flags=flag_default)
async def callback_use_card_4(callback: CallbackQuery):
    await callback.answer()
    card_info = await rq.get_player_card(callback.from_user.id)
    
    if not card_info.startswith('open_'):
        parts = callback.data.split('_')
        char_type = parts[1]
        result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
        
        user_info = await rq.get_user_info(callback.from_user.id)
        await retry_after_decorate(callback.message.edit_text)(
            text=f"<b><blockquote>🃏———<i><u>КАРТА ДЕЙСТВИЯ</u></i>———🃏</blockquote>\n\n"
                 f"Выберите игрока у которого хотите вылечить {result}</b>",
            parse_mode='HTML',
            reply_markup=await kb.use_4_card(user_info[0], callback.from_user.id, 'card4',
                                             char_type, user_info, 0))


@router.callback_query(F.data == 'PCard', PlayerState.in_game, flags=flag_default)
async def callback_buy_pcard_menu(callback: CallbackQuery):
    await callback.answer()
    info = await rq.get_money_and_pcard(callback.from_user.id)
    
    if info[1] != 0:
        await callback.answer('Вы уже использовали вторую карту действий в этой игре.')
    else:
        await retry_after_decorate(callback.message.edit_text)(
            text=f'Ваши монеты: {info[0]} 🪙\n'
                 'Выберите, какую карту вы хотите использовать:\n\n'
                 '<b><u>1️⃣ КАРТА № 1:</u></b>\n<blockquote>Поменяйте все свои нераскрытые характеристики.</blockquote>'
                 'Цена: 60 монет 🪙\n\n'
                 '<b><u>2️⃣ КАРТА № 2:</u></b>\n<blockquote>Поменяйтесь любой картой с любым из игроков.</blockquote>'
                 'Цена: 40 монет 🪙\n\n'
                 '<b><u>3️⃣ КАРТА № 3:</u></b>\n<blockquote>Поменяйте значение любой характеристики на одно из 3 '
                 'предложенных.</blockquote>Цена: 40 монет 🪙\n\n'
                 '<b><u>4️⃣ КАРТА № 4:</u></b>\n<blockquote>Вылечите фобию/болезнь/зависимость любого игрока, '
                 'включая себя.</blockquote>'
                 'Цена: 40 монет 🪙',
            reply_markup=kb.pcard, parse_mode='HTML')


@router.callback_query(F.data.startswith('PCardUse_'), PlayerState.in_game, flags=flag_default)
async def callback_select_pcard_action(callback: CallbackQuery):
    parts = callback.data.split('_')
    action_type = parts[1]
    info = await rq.get_money_and_pcard(callback.from_user.id)
    money = info[0]

    if action_type == '1' and money > 59:
        await callback.answer()
        player_info = await rq.get_player_by_id(user_id=callback.from_user.id)
        open_player_info = [x for x in player_info if not x.startswith('open_') and not x.startswith('const_')]
        
        message_result = 'Характеристики, которые будут заменены:\n \n'
        for line in open_player_info:
            line_parts = line.split('_')
            # Исправлен SyntaxError: убраны одинарные кавычки внутри f-строки
            message_result += f'{line_parts[0]}: {line_parts[2]}\n'
            
        await retry_after_decorate(callback.message.edit_text)(
            text=f'<b>Вы уверены что хотите заменить все свои нераскрытые характеристики?\n\n'
                 f'{message_result}</b>',
            parse_mode='HTML',
            reply_markup=kb.pcard_1)
            
    elif action_type == '2' and money > 39:
        await callback.answer()
        player_info = await rq.get_player_by_id(callback.from_user.id)
        user_info = [x for x in player_info if not x.startswith('const_')]
        await retry_after_decorate(callback.message.edit_text)(
            text='<b>Выберите характеристику, которой хотите поменяться с другим игроком.</b>',
            parse_mode='HTML',
            reply_markup=await kb.pcard_23(user_info, action_type))
            
    elif action_type == '3' and money > 39:
        await callback.answer()
        player_info = await rq.get_player_by_id(callback.from_user.id)
        user_info = [x for x in player_info if not x.startswith('const_')]
        await retry_after_decorate(callback.message.edit_text)(
            text='<b>Выберите характеристику, значение которой хотите поменять.</b>',
            parse_mode='HTML',
            reply_markup=await kb.pcard_23(user_info, action_type))
            
    elif action_type == '4' and money > 39:
        await callback.answer()
        await retry_after_decorate(callback.message.edit_text)(
            text='<b>Выберите, какую из характеристик хотите вылечить.</b>',
            parse_mode='HTML',
            reply_markup=kb.pcard_4)
    else:
        await callback.answer('У вас недостаточно монет')


@router.callback_query(F.data.startswith('UsePCard2_'), PlayerState.in_game, flags=flag_default)
async def callback_use_pcard_2(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split('_')
    char_type = parts[1]
    result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
    
    data = await state.get_data()
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>Выберите игрока, с которым хотите поменяться картой: {result}</b>',
        parse_mode='HTML',
        reply_markup=await kb.use_card(data['chat_id'], callback.from_user.id,
                                       'card1', char_type, 1))


@router.callback_query(F.data.startswith('UsePCard4_'), PlayerState.in_game, flags=flag_default)
async def callback_use_pcard_4(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split('_')
    char_type = parts[1]
    result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
    
    user_info = await rq.get_user_info(callback.from_user.id)
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>Выберите игрока у которого хотите вылечить {result}</b>',
        parse_mode='HTML',
        reply_markup=await kb.use_4_card(user_info[0], callback.from_user.id, 'card4',
                                         char_type, user_info, 1))


@router.callback_query(F.data.startswith('UsePCard3_'), PlayerState.in_game, flags=flag_default)
async def callback_use_pcard_3(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    room: Room = rooms[data['chat_id']]
    parts = callback.data.split('_')
    char_type = parts[1]
    
    result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
    
    if char_type == 'gender':
        msg_text = await rq.regeneration_gender_select(room, state)
    elif char_type == 'profession':
        msg_text = await rq.regeneration_profession_select(room, state, callback.from_user.id)
    else:
        msg_text = await rq.regeneration_characteristics_select(char_type, room)
        
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>Выберите новое значение карты {result}:\n \n<blockquote>1️⃣ {msg_text[0][1]}\n \n"
             f"2️⃣ {msg_text[1][1]}\n \n3️⃣ {msg_text[2][1]}</blockquote></b>",
        reply_markup=await kb.use_3_card(msg_text, char_type, 1),
        parse_mode='HTML')


@router.callback_query(F.data == 'UsePCard1', PlayerState.in_game, flags=flag_default)
async def callback_confirm_pcard_1(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    room = rooms[(await state.get_data())['chat_id']]
    revers_info = await rq.pcard1(callback.from_user.id, room)
    await rq.use_pcard(callback.from_user.id, 60)
    
    msg_text = '<b>Характеристики, которые были заменены:\n \n'
    for x in revers_info:
        msg_text += f'{x[1]}: {x[0]}\n'
    msg_text += '</b>'
    
    await retry_after_decorate(callback.message.edit_text)(
        text=msg_text, reply_markup=kb.back_game_info, parse_mode='HTML')


@router.callback_query(F.data.startswith('card6_'), flags=flag_default)
async def callback_use_card_6(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
    if await state.get_state() != PlayerState.in_game:
        return
        
    room: Room = rooms[(await state.get_data())['chat_id']]
    card_info = await rq.get_player_card(callback.from_user.id)
    
    if not card_info.startswith('open_'):
        room.bot_open = callback.from_user.id
        await rq.use_card(callback.from_user.id)
        await retry_after_decorate(callback.message.edit_text)(
            text='<b>✅ Вы применили карту действий.\nВ следующем раунде только вы сможете открыть '
                 'ту характеристику, которую хотите, за остальных характеристику откроет бот.</b>',
            reply_markup=kb.back_game_info, parse_mode='HTML')


@router.callback_query(F.data.startswith('Card_'), flags=flag_default)
async def callback_execute_card_action(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
    if await state.get_state() != PlayerState.in_game:
        return
        
    card_info = await rq.get_player_card(callback.from_user.id)
    parts = callback.data.split('_')
    card_type = parts[1]
    is_premium = parts[4]
    
    if not card_info.startswith('open_') or is_premium == '1':
        room: Room = rooms[(await state.get_data())['chat_id']]
        
        if card_type == 'card2':
            await card_2(callback)
        elif card_type == 'card1':
            await card_1(callback, bot, room)
        elif card_type == 'card4':
            await card_4(callback, bot, room)
            
        if is_premium == '0':
            await rq.use_card(callback.from_user.id)
        else:
            await rq.use_pcard(callback.from_user.id, 40)


@router.callback_query(F.data.startswith('Use3_'), PlayerState.in_game, flags=flag_default)
async def callback_execute_card_3_generation(callback: CallbackQuery, bot: Bot, state: FSMContext):
    room = rooms[(await state.get_data())['chat_id']]
    await callback.answer()
    
    parts = callback.data.split('_')
    char_id = parts[1]
    char_type = parts[2]
    is_premium = parts[3]
    
    result = CHAR_NAMES_RU.get(char_type, '🫀 Здоровье')
    
    if char_type == 'gender':
        res = await rq.regeneration_gender(char_id, result, state, room, callback.from_user.id)
    elif char_type == 'profession':
        res = await rq.regeneration_profession(char_id, result, state, room, callback.from_user.id)
    else:
        res = await rq.regeneration_characteristics(char_id, char_type, callback.from_user.id, result, room)
        
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>Вы поменяли значение карты {result}.\nНовое значение: {res}</b>',
        reply_markup=kb.back_game_info, parse_mode='HTML')
        
    if is_premium == '0':
        await rq.use_card(callback.from_user.id)
    else:
        await rq.use_pcard(callback.from_user.id, 40)
        
    user_info = await rq.get_user_info(callback.from_user.id)
    msg = await retry_after_decorate(bot.send_message)(
        chat_id=room.chat_id,
        text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
             f'<b><i>[{user_info[1]}] <a href="tg://user?id={user_info[3]}">{html.escape(user_info[2])}</a> '
             f'сгенерировал(а) новое значение для карты {result}</i></b>',
        parse_mode="HTML"
    )
    room.round_msg.append(msg.message_id)