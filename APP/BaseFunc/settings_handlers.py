import os
import html
import time
from sqlalchemy import text
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from APP.Middlewares.throttling_middleware import flag_default, ThrottlingMiddleware
from APP.BaseFunc.settings import Settings, text_settings, PremiumSettings, text_prem_settings
import APP.BaseFunc.requests as rq
import APP.BaseFunc.keyboards as kb
from APP.Middlewares.decorators import retry_after_decorate
from aiogram.filters import Command, StateFilter
from aiogram import F, Router, Bot
from APP.BaseFunc.updates_requests import set_chat, get_chat_status
from APP.Game.func import PlayerState
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from config import admin_id, query_split, query, rooms
from aiogram.fsm.context import FSMContext

class SqlState(StatesGroup):
    sql_text = State()

class SetLists(StatesGroup):
    char_list = State()
    cataclysm_name = State() 
    cataclysm_desc = State() 
    cataclysm_delete = State()
    event_type = State()
    event_text = State()
    event_delete = State()

router = Router()

router.callback_query.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                                      throttle_time_end=4, throttle_time_other=0.2,
                                                      throttle_time_card=4))
router.message.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                               throttle_time_end=4, throttle_time_other=0.2,
                                               throttle_time_card=4))

# === ГЛОБАЛЬНЫЙ СЛОВАРЬ ПРАВ ===
RIGHTS_TEXT_DICT = {
    'Votes': 'Голосованием', 'Admins': 'Админы', 'StartPlayer': 'Запустивший',
    'Players': 'Игроки', 'Users': 'Все'
}

async def ensure_events_tables():
    async with rq.engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS premium_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id BIGINT,
                event_type INTEGER,
                event_text TEXT
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS premium_events_status (
                chat_id BIGINT PRIMARY KEY,
                is_active INTEGER DEFAULT 0
            )
        """))

async def get_rus_name_info(char: str, settings: PremiumSettings = None):
    mapping = {
        'fact': '✳ Доп. информация',
        'profession': '💼 Профессия',
        'gender': '👤 Био. информация',
        'hobbies': '🧩 Хобби',
        'baggage': '🎒 Багаж',
        'phobia': '🕷 Фобия',
        'addiction': '💊 Зависимость',
        'persona': '😎 Черта характера',
        'bunker_rooms': '🏠 Комнаты бункера',
        'supplies': '🧳 Склад бункера',
        'location_bunker': '🏞 Локация, где находится бункер'
    }
    name = mapping.get(char, '🫀 Здоровье')
    val = getattr(settings, char, 1) if settings and hasattr(settings, char) else 1
    return [name, val]

async def update_char_set(char: str, settings: PremiumSettings, new_values):
    if hasattr(settings, char):
        setattr(settings, char, new_values)
    else:
        settings.health = new_values

@router.message(Command('settings'), flags=flag_default)
async def cmd_settings(message: Message, bot: Bot):
    if message.chat.id != message.from_user.id:
        chat_members = await bot.get_chat_member_count(message.chat.id)
        await set_chat(message.chat.id, message.chat.full_name, chat_members, message.chat.username)
        try:
            status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
        except TelegramBadRequest:
            await retry_after_decorate(message.answer)(
                text='<b><blockquote>❕—— ОШИБКА ДОСТУПА ——❕</blockquote>\n\n'
                     'Пожалуйста, выдайте боту права администратора.</b>', parse_mode='HTML')
            status = ''
            
        if status not in ('administrator', 'creator'):
            await retry_after_decorate(message.answer)(
                text='<b><blockquote>❕—— ОШИБКА ДОСТУПА ——❕</blockquote>\n\n'
                     'Настройки чата доступны только администраторам и владельцу.</b>', parse_mode='HTML')
        else:
            try:
                chat_link = f'<a href="t.me/{message.chat.username}">{message.chat.full_name}</a>' if message.chat.username else f'{message.chat.full_name}'
                await retry_after_decorate(bot.send_message)(
                    chat_id=message.from_user.id,
                    text=f'<b><i>Открыты настройки чата {chat_link}:\n\n'
                         '  ⏳  Настройки таймеров\n'
                         '  🪪  Настройки прав участников\n'
                         '  🖼  Настройки игры</i></b>\n',
                    reply_markup=await kb.all_settings(message.chat.id),
                    disable_web_page_preview=True,
                    parse_mode='HTML')
                await rq.set_user_chat(message.from_user.id, message.chat.id)
                await retry_after_decorate(message.answer)(
                    text='<b>Настройки чата отправлены в личные сообщения с ботом</b>',
                    reply_markup=kb.chat_game,
                    parse_mode='HTML')
            except TelegramForbiddenError:
                await retry_after_decorate(message.answer)(
                    text='<b>💢 Я не могу отправить вам настройки, пока вы не начали со мной диалог в ЛС!</b>',
                    reply_markup=kb.chat_game,
                    parse_mode='HTML')
    else:
        chat_info = await rq.select_user_chat_info(message.from_user.id)
        if chat_info is not None:
            chat_link = f'<a href="t.me/{chat_info[2]}">{chat_info[1]}</a>' if chat_info[2] and chat_info[2] != 'None' else f'{chat_info[1]}'
            await retry_after_decorate(message.answer)(
                text=f'<b><i>Открыты настройки чата {chat_link}:\n\n'
                     '  ⏳  Настройки таймеров\n'
                     '  🪪  Настройки прав участников\n'
                     '  🖼  Настройки игры</i></b>\n',
                reply_markup=await kb.all_settings(chat_info[0]),
                disable_web_page_preview=True,
                parse_mode='HTML')
        else:
            await retry_after_decorate(message.answer)(
                text='<b>Отправьте команду /settings в чате, который хотите привязать.</b>\n',
                parse_mode='HTML')

@router.callback_query(F.data.startswith('settings_'), flags=flag_default)
async def callback_all_settings(callback: CallbackQuery):
    await callback.answer()
    chat_info = await rq.select_user_chat_info(callback.from_user.id)
    if chat_info is None:
        return
    chat_link = f'<a href="t.me/{chat_info[2]}">{chat_info[1]}</a>' if chat_info[2] and chat_info[2] != 'None' else f'{chat_info[1]}'
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b><i>Открыты настройки чата {chat_link}:\n\n'
             '  ⏳  Настройки таймеров\n'
             '  🪪  Настройки прав участников\n'
             '  🖼  Настройки игры</i></b>\n',
        reply_markup=await kb.all_settings(chat_info[0]),
        disable_web_page_preview=True,
        parse_mode='HTML')

@router.callback_query(F.data.startswith('buy_premium_'), flags=flag_default)
async def buy_premium_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    stars_price = int(os.getenv('PREMIUM_STARS_PRICE', 100))
    prices = [LabeledPrice(label="Премиум на 1 месяц", amount=stars_price)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Премиум статус 👑",
        description="Разблокировка премиум функций на 30 дней: свои характеристики, концовки от ИИ, кастомные катастрофы и события.",
        payload=f"premium_{chat_id}",
        provider_token="", 
        currency="XTR",
        prices=prices
    )

@router.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def on_successful_payment(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    if payload and payload.startswith('premium_'):
        chat_id = int(payload.split('_')[1])
        await rq.activate_premium_chat(chat_id, duration_days=30)
        await message.answer("✅ <b>Оплата прошла успешно! Премиум статус для чата активирован на 30 дней.</b>\n"
                             "Теперь вы можете вернуться в меню настроек и персонализировать игру.", parse_mode="HTML")

@router.callback_query(F.data.startswith('prem_settings'), flags=flag_default)
async def callback_prem_settings_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_id = int(callback.data.split('_')[2])
    
    is_active = await rq.check_premium_expiration(chat_id)
    chat_status = await get_chat_status(chat_id)
    
    if chat_status != 'premium' or not is_active:
        stars_price = int(os.getenv('PREMIUM_STARS_PRICE', 100))
        buy_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐️ Купить Премиум ({stars_price} XTR)", callback_data=f"buy_premium_{chat_id}")],
            [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
        ])
        await retry_after_decorate(callback.message.edit_text)(
            text="<b>🤔 Чтоб установить свои характеристики, случайные события и концовку ИИ, необходима подписка.\n\n"
                 "Вы можете приобрести премиум-доступ для этого чата на 1 месяц за Telegram Stars! ⭐️</b>",
            reply_markup=buy_kb,
            parse_mode='HTML')
    else:
        data = await state.get_data()
        required_keys = {'set_chat_id', 'type_char', 'char_list'}
        keys_to_delete = set(data.keys()) - required_keys
        for key in keys_to_delete:
            del data[key]
            
        await state.update_data(set_chat_id=chat_id)
        
        full_prem_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭", callback_data=f'prem_char_{chat_id}'),
             InlineKeyboardButton(text="🏠", callback_data=f'prem_bunker_{chat_id}'),
             InlineKeyboardButton(text="💣", callback_data=f'prem_cataclysm_{chat_id}'),
             InlineKeyboardButton(text="🎲", callback_data=f'prem_events_{chat_id}'),
             InlineKeyboardButton(text="🤖", callback_data=f'prem_ai_{chat_id}')],
            [InlineKeyboardButton(text="Назад ↩", callback_data=f'settings_{chat_id}')]
        ])
        
        await retry_after_decorate(callback.message.edit_text)(
            text="<b>🤔 Что хотите настроить?\n\n"
                 "    🎭 Характеристики игроков\n"
                 "    🏠 Характеристики бункера\n"
                 "    💣 Катастрофы\n"
                 "    🎲 Случайные события\n"
                 "    🤖 Формат ИИ-концовки</b>",
            reply_markup=full_prem_kb,
            parse_mode='HTML')

@router.callback_query(F.data.startswith('timer_settings'), flags=flag_default)
async def callback_timer_settings_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    settings = Settings(await rq.select_chat_settings(chat_id))
    await retry_after_decorate(callback.message.edit_text)(
        text='<b><i>✏️ Введите команду:\n'
             '<code>Таймер [номер пункта] [время в сек]</code>\n\n'
             f'   1️⃣ [{settings.time_start} сек] Время на ознакомление с картами\n'
             f'   2️⃣ [{settings.time_open} сек] Время раскрытия характеристик\n'
             f'   3️⃣ [{settings.time_discussion} сек] Время на обсуждение\n'
             f'   4️⃣ [{settings.time_votes} сек] Время на голосование\n'
             f'   5️⃣ [{settings.time_round} сек] Время между раундами\n\n'
             '📝 Пример: <code>Таймер 3 120</code>\n(Время на обсуждение 120 сек)\n\n'
             '-----------------------------------------------------\n\n'
             f'✏️ Введите команду:\n'
             '<code>Игроки [номер пункта] [кол-во игроков]</code>\n\n'
             f'   6️⃣ [{settings.max_players}] Макс. кол-во игроков\n'
             f'   7️⃣ [{settings.min_players}] Мин. кол-во игроков\n\n'
             '📝 Пример: <code>Игроки 6 5</code>\n(Мин. кол-во игроков 5)</i></b>',
        parse_mode='HTML',
        reply_markup=await kb.back_settings(chat_id))

@router.callback_query(F.data.startswith('rights_settings'), flags=flag_default)
async def callback_rights_settings_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    settings = Settings(await rq.select_chat_settings(chat_id))
    await retry_after_decorate(callback.message.edit_text)(
        text='<b>🔘 Воспользуйтесь кнопками, чтоб поменять настройки:\n\n'
             f'   1️⃣ [{RIGHTS_TEXT_DICT[settings.start_game]}] - Запуск игры\n'
             f'   2️⃣ [{RIGHTS_TEXT_DICT[settings.stop_game]}] - <i>Остановка игры</i>\n'
             f'   3️⃣ [{RIGHTS_TEXT_DICT[settings.stop_register]}] - <i>Остановка регистрации</i>\n'
             f'   4️⃣ [{RIGHTS_TEXT_DICT[settings.stop_discussion]}] - <i>Остановка обсуждения</i>\n'
             f'   5️⃣ [{RIGHTS_TEXT_DICT[settings.next_round]}] - <i>Пропуск голосования</i>\n'
             f'   6️⃣ [{RIGHTS_TEXT_DICT[settings.extend_register]}] - <i>Продление набор в игру</i>\n'
             f'   7️⃣ [{RIGHTS_TEXT_DICT[settings.extend_discussion]}] - <i>Продление обсуждения</i>\n\n'
             '<blockquote expandable><i>[Админ] - права имеет только Админы.\n\n'
             '[Запустивший] - права имеют Админы и Запустивший игру.\n\n'
             '[Голосованием] - определяется путем голосования.\n\n'
             '[Игроки] - права имеют все Админы и участники игры.</i>'
             '</blockquote></b>',
        parse_mode='HTML',
        reply_markup=await kb.rights_settings(settings=settings, chat_id=chat_id))

@router.callback_query(F.data.startswith('game_settings'), flags=flag_default)
async def callback_game_settings_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    settings = Settings(await rq.select_chat_settings(chat_id))
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>🔘 Воспользуйтесь кнопками, чтоб изменить настройки:\n\n'
             f'<i>🔴 - Выключено\n'
             f'🟢 - Включено</i>\n\n'
             f'1️⃣ [{"🟢" if settings.pin_votes_msg else "🔴"}] - <i>Закреплять сообщение с голосованием</i>\n'
             f'2️⃣ [{"🟢" if settings.pin_open_char else "🔴"}] - <i>Закреплять сообщение с открытыми характеристиками '
             f'всех игроков</i>\n'
             f'3️⃣ [{"🟢" if settings.anonymous_votes else "🔴"}] - <i>Анонимное голосование</i>\n'
             f'4️⃣ [{"🟢" if settings.delete_messages else "🔴"}] - <i>Удаление сообщений пользователей, '
             f'не участвующих в игре</i>\n'
             f'5️⃣ [{"🟢" if settings.delete_round_msgs else "🔴"}] - <i>Удаление сообщений предыдущего раунда</i>\n'
             f'6️⃣ [{"🟢" if settings.pin_info_game_msg else "🔴"}] - <i>Закреплять сообщения с инфо о игре</i>\n'
             f'7️⃣ [{"🟢" if settings.pin_reg_msg else "🔴"}] - <i>Закреплять сообщение с регистрацией</i></b>',
        parse_mode='HTML',
        reply_markup=await kb.game_settings(settings, chat_id))

@router.callback_query(F.data.startswith('GS+'), flags=flag_default)
async def callback_gs_toggle(callback: CallbackQuery):
    await callback.answer()
    action = callback.data.split('+')[1]
    chat_id = callback.data.split('+')[2]
    settings = Settings(await rq.select_chat_settings(chat_id))
    
    if hasattr(settings, action) and isinstance(getattr(settings, action), bool):
        setattr(settings, action, not getattr(settings, action))
        
    text_s = await text_settings(settings)
    await rq.update_settings(text_s, chat_id)
    
    if int(chat_id) in rooms:
        rooms[int(chat_id)].settings = settings
        
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>🔘 Воспользуйтесь кнопками, чтоб изменить настройки:\n\n'
             f'<i>🔴 - Выключено\n🟢 - Включено</i>\n\n'
             f'1️⃣ [{"🟢" if settings.pin_votes_msg else "🔴"}] - <i>Закреплять сообщение с голосованием</i>\n'
             f'2️⃣ [{"🟢" if settings.pin_open_char else "🔴"}] - <i>Закреплять сообщение с открытыми характеристиками '
             f'всех игроков</i>\n'
             f'3️⃣ [{"🟢" if settings.anonymous_votes else "🔴"}] - <i>Анонимное голосование</i>\n'
             f'4️⃣ [{"🟢" if settings.delete_messages else "🔴"}] - <i>Удаление сообщений пользователей, '
             f'не участвующих в игре</i>\n'
             f'5️⃣ [{"🟢" if settings.delete_round_msgs else "🔴"}] - <i>Удаление сообщений предыдущего раунда</i>\n'
             f'6️⃣ [{"🟢" if settings.pin_info_game_msg else "🔴"}] - <i>Закреплять сообщения с инфо о игре</i>\n'
             f'7️⃣ [{"🟢" if settings.pin_reg_msg else "🔴"}] - <i>Закреплять сообщение с регистрацией</i></b>',
        parse_mode='HTML',
        reply_markup=await kb.game_settings(settings, chat_id))

@router.message(F.text.lower().startswith('таймер '), flags=flag_default)
async def msg_timer_settings_update(message: Message):
    chat_info = await rq.select_user_chat_info(message.from_user.id)
    if chat_info is None:
        await retry_after_decorate(message.answer)(
            text='<b>Отправьте команду /settings в чате, который хотите привязать.</b>\n',
            parse_mode='HTML')
        return

    parts = message.text.split(' ')
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        timer_id = int(parts[1])
        timer_val = int(parts[2])
        if 0 < timer_id < 6 and 9 < timer_val < 361:
            settings = Settings(await rq.select_chat_settings(chat_info[0]))
            
            if timer_id == 1: settings.time_start = timer_val
            elif timer_id == 2: settings.time_open = timer_val
            elif timer_id == 3: settings.time_discussion = timer_val
            elif timer_id == 4: settings.time_votes = timer_val
            elif timer_id == 5: settings.time_round = timer_val
                
            text_s = await text_settings(settings)
            await rq.update_settings(text_s, chat_info[0])
            if int(chat_info[0]) in rooms:
                rooms[int(chat_info[0])].settings = settings
                
            await retry_after_decorate(message.answer)(
                text='<b><i>✏️ Введите команду:\n'
                     '<code>Таймер [номер пункта] [время в сек]</code>\n\n'
                     f'   1️⃣ [{settings.time_start} сек] Время на ознакомление с картами\n'
                     f'   2️⃣ [{settings.time_open} сек] Время раскрытия характеристик\n'
                     f'   3️⃣ [{settings.time_discussion} сек] Время на обсуждение\n'
                     f'   4️⃣ [{settings.time_votes} сек] Время на голосование\n'
                     f'   5️⃣ [{settings.time_round} сек] Время между раундами\n\n'
                     '📝 Пример: <code>Таймер 3 120</code>\n(Время на обсуждение 120 сек)\n\n'
                     '-----------------------------------------------------\n\n'
                     f'✏️ Введите команду:\n'
                     '<code>Игроки [номер пункта] [кол-во игроков]</code>\n\n'
                     f'   6️⃣ [{settings.max_players}] Макс. кол-во игроков\n'
                     f'   7️⃣ [{settings.min_players}] Мин. кол-во игроков\n\n'
                     '📝 Пример: <code>Игроки 6 5</code>\n(Мин. кол-во игроков 5)</i></b>',
                parse_mode='HTML',
                reply_markup=await kb.back_settings(chat_info[0]))
            return

    await retry_after_decorate(message.answer)(
        text='<b><blockquote>❕—— ОШИБКА НАСТРОЕК ——❕</blockquote>\n\n'
             '✏️ Пожалуйста введите команду как в примере:\n\n'
             'Команда:\n<code>Таймер [номер пункта] [время в сек]</code>\n\n'
             '📝 Пример:\n<code>Таймер 3 150</code>\n\n'
             '❗️ Учтите: <i>Время в секундах не может быть больше 360 и меньше 10</i></b>',
        parse_mode='HTML',
        reply_markup=await kb.back_settings(chat_info[0]))

@router.message(F.text.lower().startswith('игроки '), flags=flag_default)
async def msg_players_settings_update(message: Message):
    chat_info = await rq.select_user_chat_info(message.from_user.id)
    if chat_info is None:
        await retry_after_decorate(message.answer)(
            text='<b>Отправьте команду /settings в чате, который хотите привязать.</b>\n',
            parse_mode='HTML')
        return

    parts = message.text.split(' ')
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        option_id = int(parts[1])
        players_val = int(parts[2])
        if 5 < option_id < 8 and 3 < players_val < 19:
            settings = Settings(await rq.select_chat_settings(chat_info[0]))
            
            if option_id == 6: settings.max_players = players_val
            elif option_id == 7: settings.min_players = players_val
                
            text_s = await text_settings(settings)
            await rq.update_settings(text_s, chat_info[0])
            if int(chat_info[0]) in rooms:
                rooms[int(chat_info[0])].settings = settings
                
            await retry_after_decorate(message.answer)(
                text='<b><i>✏️ Введите команду:\n'
                     '<code>Таймер [номер пункта] [время в сек]</code>\n\n'
                     f'   1️⃣ [{settings.time_start} сек] Время на ознакомление с картами\n'
                     f'   2️⃣ [{settings.time_open} сек] Время раскрытия характеристик\n'
                     f'   3️⃣ [{settings.time_discussion} сек] Время на обсуждение\n'
                     f'   4️⃣ [{settings.time_votes} сек] Время на голосование\n'
                     f'   5️⃣ [{settings.time_round} сек] Время между раундами\n\n'
                     '📝 Пример: <code>Таймер 3 120</code>\n(Время на обсуждение 120 сек)\n\n'
                     '-----------------------------------------------------\n\n'
                     f'✏️ Введите команду:\n'
                     '<code>Игроки [номер пункта] [кол-во игроков]</code>\n\n'
                     f'   6️⃣ [{settings.max_players}] Макс. кол-во игроков\n'
                     f'   7️⃣ [{settings.min_players}] Мин. кол-во игроков\n\n'
                     '📝 Пример: <code>Игроки 6 5</code>\n(Мин. кол-во игроков 5)</i></b>',
                parse_mode='HTML',
                reply_markup=await kb.back_settings(chat_info[0]))
            return

    await retry_after_decorate(message.answer)(
        text='<b><blockquote>❕—— ОШИБКА НАСТРОЕК ——❕</blockquote>\n\n'
             '✏️ Пожалуйста введите команду как в примере:\n\n'
             'Команда:\n<code>Игроки [номер пункта] [кол-во игроков]</code>\n\n'
             '📝 Пример:\n<code>Игроки 6 5</code>\n\n'
             '❗️ Учтите: <i>Количество игроков не может быть больше 18 и меньше 4</i></b>',
        parse_mode='HTML',
        reply_markup=await kb.back_settings(chat_info[0]))

@router.callback_query(F.data.startswith('RS+'), flags=flag_default)
async def callback_rs_toggle(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('+')[2]
    action_id = int(callback.data.split('+')[1])
    settings = Settings(await rq.select_chat_settings(chat_id))

    def toggle(current, val1, val2):
        return val2 if current == val1 else val1

    if action_id == 1: settings.start_game = toggle(settings.start_game, 'Users', 'Admins')
    elif action_id == 2: settings.stop_game = toggle(settings.stop_game, 'Votes', 'Admins')
    elif action_id == 3: settings.stop_register = toggle(settings.stop_register, 'Admins', 'StartPlayer')
    elif action_id == 4: settings.stop_discussion = toggle(settings.stop_discussion, 'Votes', 'Admins')
    elif action_id == 5: settings.next_round = toggle(settings.next_round, 'Votes', 'Admins')
    elif action_id == 6: settings.extend_register = toggle(settings.extend_register, 'StartPlayer', 'Admins')
    elif action_id == 7: settings.extend_discussion = toggle(settings.extend_discussion, 'Admins', 'Players')

    text_s = await text_settings(settings)
    await rq.update_settings(text_s, chat_id)
    if int(chat_id) in rooms:
        rooms[int(chat_id)].settings = settings
        
    await retry_after_decorate(callback.message.edit_text)(
        text='<b>🔘 Воспользуйтесь кнопками, чтоб поменять настройки:\n\n'
             f'   1️⃣ [{RIGHTS_TEXT_DICT[settings.start_game]}] - Запуск игры\n'
             f'   2️⃣ [{RIGHTS_TEXT_DICT[settings.stop_game]}] - <i>Остановка игры</i>\n'
             f'   3️⃣ [{RIGHTS_TEXT_DICT[settings.stop_register]}] - <i>Остановка регистрации</i>\n'
             f'   4️⃣ [{RIGHTS_TEXT_DICT[settings.stop_discussion]}] - <i>Остановка обсуждения</i>\n'
             f'   5️⃣ [{RIGHTS_TEXT_DICT[settings.next_round]}] - <i>Пропуск голосования</i>\n'
             f'   6️⃣ [{RIGHTS_TEXT_DICT[settings.extend_register]}] - <i>Продление набор в игру</i>\n'
             f'   7️⃣ [{RIGHTS_TEXT_DICT[settings.extend_discussion]}] - <i>Продление обсуждения</i>\n\n'
             '<blockquote expandable><i>[Админ] - права имеет только Админы.\n\n'
             '[Запустивший] - права имеют Админы и Запустивший игру.\n\n'
             '[Голосование] - определяется путем голосования.</i>'
             '</blockquote></b>',
        parse_mode='HTML',
        reply_markup=await kb.rights_settings(settings=settings, chat_id=chat_id))

@router.callback_query(F.data.startswith('mylist+'), flags=flag_default)
async def callback_show_mylist(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    char_type = callback.data.split('+')[1]
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    char_name_info = await get_rus_name_info(char_type, settings)
    premium_char = await rq.select_prem_char(chat_id, char_type)
    
    if premium_char == 'default':
        await retry_after_decorate(callback.message.edit_text)(
            text=f"<b><i>У вас еще не установлен список для характеристик «{char_name_info[0]}», хотите установить?</i></b>",
            reply_markup=await kb.set_lists(char_type, chat_id),
            parse_mode='HTML')
    else:
        status_emoji = '🟢 Активно' if char_name_info[1] else '🔴 Неактивно'
        await retry_after_decorate(callback.message.edit_text)(
            text=f"<b>📋 Ваш список для характеристики\n"
                 f"«{char_name_info[0]}»:\n\n<blockquote expandable>[{', '.join(premium_char.split('_'))}]</blockquote>\n\n"
                 f"Статус: {status_emoji}</b>",
            reply_markup=await kb.update_lists(char_type, chat_id, char_name_info[1]),
            parse_mode='HTML')

@router.callback_query(F.data.startswith('SetMylist+'), flags=flag_default)
async def callback_set_mylist_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    char_type = callback.data.split('+')[1]
    await state.set_state(SetLists.char_list)
    await state.update_data(type_char=char_type)
    
    data = await state.get_data()
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>Отправьте список характеристик для \n«{char_type}»:\n\n"
             "<i>📝 Пример:\n<code>    Хоккей\n    Бильярд\n    Футбол\n    Баскетбол</code></i>\n"
             "(Пример для установки списка Хобби)\n\n"
             "<i><u>ВАЖНО</u>: Чтобы список сохранился корректно, убедитесь, что каждая из"
             " характеристик должна находиться на новой строке</i></b>",
        reply_markup=await kb.back_set_lists(data['set_chat_id']),
        parse_mode='HTML')

@router.message(StateFilter(SetLists.char_list))
async def msg_char_list_receive(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'): return
    
    char_list = [x.strip() for x in message.text.split('\n') if x.strip()]
    data = await state.get_data()
    
    if any(char in message.text for char in ['_', '/', '<', '>', "'", '"']):
        await retry_after_decorate(message.answer)(
            text=f"<b>🚫 Нельзя использовать следующие символы:\n"
                 f"  [ _ ]    [ / ]    [ &lt; ]    [ &gt; ]    [ \" ]    [ ' ]</b>\n\n"
                 f"📋 Пожалуйста, отправьте список повторно, не используя данные символы.",
            parse_mode='HTML')
        return
        
    type_char = data['type_char']
    
    if len(char_list) < 18 and type_char not in ['bunker_rooms', 'supplies', 'location_bunker']:
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Минимальная длина списка 18 элементов\n\n"
                 "📋 Пожалуйста, отправьте список повторно.</b>",
            parse_mode='HTML')
        return
        
    if len(char_list) < 3 and type_char == 'bunker_rooms':
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Минимальная длина списка 3 элемента\n\n"
                 "📋 Пожалуйста, отправьте список повторно.</b>",
            parse_mode='HTML')
        return
        
    if len(char_list) < 2 and type_char == 'supplies':
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Минимальная длина списка 2 элемента\n\n"
                 "📋 Пожалуйста, отправьте список повторно.</b>",
            parse_mode='HTML')
        return
        
    if len(message.text) > 2000:
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Максимальная длина списка 2000 символов\n\n"
                 "📋 Пожалуйста, отправьте список короче.</b>",
            parse_mode='HTML')
        return
        
    await state.update_data(char_list=char_list)
    char_name_info = await get_rus_name_info(type_char)
    
    await retry_after_decorate(message.answer)(
        text=f"<b>📋 Ваш список для характеристики\n"
             f"«{char_name_info[0]}»:\n\n<blockquote expandable>[{', '.join(char_list)}]</blockquote>\n\n"
             "❔ Вы уверены что хотите установить этот список?\n✏️ Чтоб поменять список, отправьте новый текст.</b>",
        reply_markup=await kb.yes_char_set(type_char, data['set_chat_id']),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('UpdateStatusChar+'), flags=flag_default)
async def callback_update_status_char(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    char_type = callback.data.split('+')[1]
    value = (callback.data.split('+')[2] == 'on')
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    await update_char_set(char_type, settings, value)
    
    text_s = await text_prem_settings(settings)
    await rq.update_prem_settings(text_s, chat_id)
    
    char_name_info = await get_rus_name_info(char_type, settings)
    premium_char = await rq.select_prem_char(chat_id, char_type)
    status_emoji = '🟢 Активно' if char_name_info[1] else '🔴 Неактивно'
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>📋 Ваш список для характеристики\n"
             f"«{char_name_info[0]}»:\n\n<blockquote expandable>[{', '.join(premium_char.split('_'))}]</blockquote>\n\n"
             f"Статус: {status_emoji}</b>",
        reply_markup=await kb.update_lists(char_type, chat_id, char_name_info[1]),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('prem_char_'), flags=flag_default)
async def callback_prem_char_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>🎭 Выберите характеристику для настройки:\n\n"
             "  💼 - Профессия\n"
             "  👤 - Био информация\n"
             "  ✳ - Доп. информация\n"
             "  🧩 - Хобби\n"
             "  🎒 - Багаж\n"
             "  🫀 - Здоровье\n"
             "  🕷 - Фобия\n"
             "  💊 - Зависимость\n"
             "  😎 - Черта характера</b>",
        reply_markup=await kb.my_list(chat_id),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('prem_bunker_'), flags=flag_default)
async def callback_prem_bunker_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>🎭 Выберите характеристику для настройки:\n\n"
             "  🏠 - Комнаты бункера\n"
             "  🧳 - Склад бункера\n"
             "  🏞 - Локация, где находится бункер</b>",
        reply_markup=await kb.my_bunker_list(chat_id),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('charset+'), flags=flag_default)
async def callback_charset_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.set_state(None)
    
    chat_id = data['set_chat_id']
    char_type = callback.data.split('+')[1]
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    await update_char_set(char_type, settings, True)
    
    char_name_info = await get_rus_name_info(char_type)
    text_s = await text_prem_settings(settings)
    
    await rq.update_prem_settings(text_s, chat_id)
    await rq.update_prem_char(char_type, chat_id, '_'.join(data['char_list']))
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>📋 Ваш список для характеристики\n"
             f"«{char_name_info[0]}»:\n\n<blockquote expandable>"
             f"[{', '.join(data['char_list'])}]</blockquote>\n\n"
             f"Статус: 🟢 Активно</b>",
        reply_markup=await kb.off_set(data['type_char'], chat_id, 1),
        parse_mode='HTML')

# === ЛОГИКА РАЗДЕЛЬНОГО ДОБАВЛЕНИЯ КАТАСТРОФ ===
@router.callback_query(F.data.startswith('prem_cataclysm_'), flags=flag_default)
async def callback_prem_cataclysm_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    cataclysms = await rq.select_prem_char(chat_id, 'cataclysm')

    if cataclysms == 'default':
        await retry_after_decorate(callback.message.edit_text)(
            text="<b><i>У вас еще не установлен список для катастроф, хотите установить?</i></b>",
            reply_markup=await kb.cataclysm_set(chat_id),
            parse_mode='HTML')
    else:
        status_emoji = '🟢 Активно' if settings.cataclysm else '🔴 Неактивно'
        await retry_after_decorate(callback.message.edit_text)(
            text=f"<b>📋 Ваш список катастроф:\n\n<blockquote expandable>"
                 f"[{', '.join([x.split('+')[0] for x in cataclysms.split('_')])}]"
                 f"</blockquote>\n\nСтатус: {status_emoji}</b>",
            reply_markup=await kb.set_cataclysm(chat_id, settings.cataclysm),
            parse_mode='HTML')

@router.callback_query(F.data.startswith('set_cataclysm_'), flags=flag_default)
async def callback_set_cataclysm_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    await state.set_state(SetLists.cataclysm_name)
    await state.update_data(set_chat_id=chat_id)
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>Отправьте НАЗВАНИЕ катастрофы:\n\n"
             "  📝 Пример:\n"
             "<code>Астероидная атака</code>\n\n"
             "🚫 Учтите, нельзя использовать символы:\n"
             f"  [ _ ]    [ / ]    [ &lt; ]    [ &gt; ]    [ \" ]    [ ' ]    [ + ]</b>",
        reply_markup=await kb.my_cataclysm_list(chat_id),
        parse_mode='HTML')

@router.message(StateFilter(SetLists.cataclysm_name))
async def msg_cataclysm_name_receive(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'): return
    
    if any(char in message.text for char in ['_', '/', '<', '>', "'", '"', '+']):
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Нельзя использовать спецсимволы. Отправьте название снова.</b>", parse_mode='HTML')
        return
        
    await state.update_data(cataclysm_name=message.text.strip())
    await state.set_state(SetLists.cataclysm_desc)
    
    data = await state.get_data()
    await retry_after_decorate(message.answer)(
        text="<b>Отлично! Теперь отправьте ОПИСАНИЕ для этой катастрофы.</b>\n\n"
             "🚫 Пожалуйста, не используйте спецсимволы (_ / < > \" ' +)",
        reply_markup=await kb.my_cataclysm_list(data.get('set_chat_id')),
        parse_mode='HTML')

@router.message(StateFilter(SetLists.cataclysm_desc))
async def msg_cataclysm_desc_receive(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'): return
    
    if any(char in message.text for char in ['_', '/', '<', '>', "'", '"', '+']):
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Нельзя использовать спецсимволы. Отправьте описание снова.</b>", parse_mode='HTML')
        return
        
    data = await state.get_data()
    cat_name = data.get('cataclysm_name')
    cat_desc = message.text.strip()
    await state.update_data(cataclysm_desc=cat_desc)
    
    await retry_after_decorate(message.answer)(
        text=f"<b>❔ Вы уверены, что хотите добавить данную катастрофу?\n\n"
             f"<u><i>НАЗВАНИЕ</i></u>: {cat_name}\n\n"
             f"<u><i>ОПИСАНИЕ</i></u>:\n{cat_desc}</b>",
        reply_markup=await kb.add_cataclysm(data.get('set_chat_id')),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('add_cataclysm_'), flags=flag_default)
async def callback_add_cataclysm_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    settings.cataclysm = True
    text_s = await text_prem_settings(settings)
    await rq.update_prem_settings(text_s, chat_id)
    
    cat_combined = f"{data['cataclysm_name']}+{data['cataclysm_desc']}"
    cataclysms = await rq.update_prem_cataclysm(chat_id, cat_combined)
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>☑️ Катастрофа добавлена\n\n📋 Ваш список для катастроф:\n\n<blockquote expandable>"
             f"[{', '.join([x.split('+')[0] for x in cataclysms.split('_')])}]</blockquote>\n\n"
             f"Статус: 🟢 Активно</b>",
        reply_markup=await kb.set_cataclysm(chat_id, 1),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('UpdateStatusCataclysm+'), flags=flag_default)
async def callback_update_status_cataclysm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    char_type = callback.data.split('+')[1]
    value = (callback.data.split('+')[2] == 'on')
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    settings.cataclysm = value
    text_s = await text_prem_settings(settings)
    await rq.update_prem_settings(text_s, chat_id)
    
    premium_char = await rq.select_prem_char(chat_id, char_type)
    status_emoji = '🟢 Активно' if settings.cataclysm else '🔴 Неактивно'
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>📋 Ваш список катастроф:\n\n"
             f"<blockquote expandable>[{', '.join([x.split('+')[0] for x in premium_char.split('_')])}]</blockquote>"
             f"\n\nСтатус: {status_emoji}</b>",
        reply_markup=await kb.set_cataclysm(chat_id, settings.cataclysm),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('delete_cataclysm_'), flags=flag_default)
async def callback_delete_cataclysm_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    premium_char = await rq.select_prem_char(chat_id, 'cataclysm')
    
    await state.set_state(SetLists.cataclysm_delete)
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>📋 Ваш список катастроф:\n\n"
             f"<blockquote expandable>[{', '.join([x.split('+')[0] for x in premium_char.split('_')])}]</blockquote>"
             f"\n\n✏️ Введите название катастрофы, которую хотите исключить из списка.\n\n"
             f"🔘 Если вы хотите очистить список полностью, воспользуйтесь кнопкой ниже.</b>",
        reply_markup=await kb.delete_cataclysm(chat_id),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('dellAll_cataclysm_'), flags=flag_default)
async def callback_del_all_cataclysm_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.set_state(None)
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>📋 Вы уверены, что хотите полностью очистить список катастроф?</b>",
        reply_markup=await kb.del_all_cataclysm(data['set_chat_id']),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('del_cataclysms_'), flags=flag_default)
async def callback_del_all_cataclysms(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = data['set_chat_id']
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    settings.cataclysm = False
    text_s = await text_prem_settings(settings)
    
    await rq.update_prem_settings(text_s, chat_id)
    await rq.update_cataclysm(chat_id, 'default')
    
    await retry_after_decorate(callback.message.answer)(
        text="<b>☑️ Вы полностью очистили список катастроф.\n\n"
             "✏️ Чтоб использовать свои катастрофы, добавьте в список хотя бы одну.</b>",
        reply_markup=await kb.cataclysm_set(chat_id),
        parse_mode='HTML')

@router.message(StateFilter(SetLists.cataclysm_delete))
async def msg_cataclysm_delete_receive(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'): return
    
    data = await state.get_data()
    chat_id = data['set_chat_id']
    premium_char = await rq.select_prem_char(chat_id, 'cataclysm')
    
    cataclysm_dict = {x.split('+')[0].lower(): x.split('+')[1] for x in premium_char.split('_')}
    target = message.text.lower().strip()
    
    if target in cataclysm_dict:
        del cataclysm_dict[target]
        settings = PremiumSettings(await rq.select_prem_settings(chat_id))
        
        if cataclysm_dict:
            update_text = '_'.join([f'{k}+{v}' for k, v in cataclysm_dict.items()])
            await rq.update_cataclysm(chat_id, update_text)
            status_emoji = '🟢 Активно' if settings.cataclysm else '🔴 Неактивно'
            await retry_after_decorate(message.answer)(
                text=f"<b>☑️ Катастрофа «{message.text}» исключена из списка\n\n"
                     f"📋 Ваш список катастроф:\n\n"
                     f"<blockquote expandable>[{', '.join([x.split('+')[0] for x in update_text.split('_')])}]"
                     f"</blockquote>\n\nСтатус: {status_emoji}</b>",
                reply_markup=await kb.set_cataclysm(chat_id, settings.cataclysm),
                parse_mode='HTML')
        else:
            settings.cataclysm = False
            text_s = await text_prem_settings(settings)
            await rq.update_prem_settings(text_s, chat_id)
            await rq.update_cataclysm(chat_id, 'default')
            await retry_after_decorate(message.answer)(
                text="<b>☑️ Вы полностью очистили список катастроф.\n\n"
             "✏️ Чтоб использовать свои катастрофы, добавьте в список хотя бы одну.</b>",
                reply_markup=await kb.cataclysm_set(chat_id),
                parse_mode='HTML')
    else:
        await retry_after_decorate(message.answer)(
            text=f"<b>❌ В вашем списке нет катастрофы с названием «{message.text}»\n"
                 f"✏️ Пожалуйста введите название правильно!\n\n📋 Ваш список катастроф:\n\n<blockquote expandable>"
                 f"[{', '.join([x.split('+')[0] for x in premium_char.split('_')])}]</blockquote></b>",
            parse_mode='HTML')

@router.callback_query(F.data.startswith('prem_ai_'), flags=flag_default)
async def callback_prem_ai_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>🤖 Настройка формата истории ИИ:\n\n"
             "  • Длинный рассказ (~3500 символов) - детальное художественное описание.\n"
             "  • Короткий прогноз (~1200 символов) - сухая и ёмкая аналитика.\n\n"
             "<i>Нажмите на кнопку ниже, чтобы переключить режим.</i></b>",
        reply_markup=await kb.prem_ai_settings(chat_id, settings.ai_format),
        parse_mode='HTML')

@router.callback_query(F.data.startswith('UpdateAIFormat_'), flags=flag_default)
async def callback_update_ai_format(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split('_')
    chat_id = parts[1]
    new_format = int(parts[2])
    
    settings = PremiumSettings(await rq.select_prem_settings(chat_id))
    settings.ai_format = new_format
    text_s = await text_prem_settings(settings)
    await rq.update_prem_settings(text_s, chat_id)
    
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>🤖 Настройка формата истории ИИ:\n\n"
             "  • Длинный рассказ (~3500 символов) - детальное художественное описание.\n"
             "  • Короткий прогноз (~1200 символов) - сухая и ёмкая аналитика.\n\n"
             "<i>Нажмите на кнопку ниже, чтобы переключить режим.</i></b>",
        reply_markup=await kb.prem_ai_settings(chat_id, settings.ai_format),
        parse_mode='HTML')


# =====================================================================
#             СИСТЕМА КАСТОМНЫХ СОБЫТИЙ (ОБНОВЛЕННАЯ ЛОГИКА)
# =====================================================================

async def render_events_menu(bot: Bot, chat_id_target: int, user_id: int, edit_message: Message = None):
    await ensure_events_tables()
    async with rq.engine.connect() as conn:
        is_active = await conn.scalar(text("SELECT is_active FROM premium_events_status WHERE chat_id = :chat_id"), {'chat_id': chat_id_target})
        is_active = is_active if is_active is not None else 0
        
        res = await conn.execute(text("SELECT id, event_text FROM premium_events WHERE chat_id = :chat_id"), {'chat_id': chat_id_target})
        events = res.fetchall()
        events_count = len(events)

    status_emoji = '🟢 Активно' if is_active else '🔴 Неактивно'
    
    buttons = []
    if events_count > 0:
        buttons.append([InlineKeyboardButton(text="Изменить ✏️", callback_data=f'edit_events_menu_{chat_id_target}')])
        buttons.append([InlineKeyboardButton(text="Выключить 🔴" if is_active else "Включить 🟢", callback_data=f'ToggleEvents_{chat_id_target}_{0 if is_active else 1}')])
    else:
        buttons.append([InlineKeyboardButton(text="Установить ➕", callback_data=f'set_event_{chat_id_target}')])
        
    buttons.append([InlineKeyboardButton(text="К настройкам ⚙️", callback_data=f'prem_settings_{chat_id_target}')])
    
    kb_events = InlineKeyboardMarkup(inline_keyboard=buttons)

    if events_count == 0:
        display_text = "<i>Список пуст. Добавьте свои первые события!</i>"
    else:
        events_str = ""
        for ev in events:
            events_str += f"ID {ev[0]}: {ev[1]}\n"
        
        if len(events_str) > 3500:
            file = BufferedInputFile(events_str.encode('utf-8'), filename=f"events_list_{chat_id_target}.txt")
            await bot.send_document(chat_id=user_id, document=file, caption="Ваши события не влезли в сообщение.")
            display_text = "<i>Список слишком длинный, поэтому он отправлен файлом выше ☝️</i>"
        else:
            display_text = f"<blockquote expandable>{html.escape(events_str)}</blockquote>"

    menu_text = (f"<b>🎲 Настройка случайных событий:\n\n"
                 f"Добавлено событий: {events_count}\n"
                 f"Статус: {status_emoji}\n\n"
                 f"Собственные события используются ВМЕСТО стандартных, пока они не закончатся в текущей игре.\n\n"
                 f"📋 Список добавленных событий:</b>\n{display_text}")

    if edit_message:
        await retry_after_decorate(edit_message.edit_text)(text=menu_text, reply_markup=kb_events, parse_mode='HTML')
    else:
        await retry_after_decorate(bot.send_message)(chat_id=user_id, text=menu_text, reply_markup=kb_events, parse_mode='HTML')


@router.callback_query(F.data.startswith('prem_events_'), flags=flag_default)
async def callback_prem_events_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    chat_id = int(callback.data.split('_')[2])
    await render_events_menu(bot, chat_id, callback.from_user.id, callback.message)


@router.callback_query(F.data.startswith('ToggleEvents_'), flags=flag_default)
async def callback_toggle_events(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    parts = callback.data.split('_')
    chat_id = int(parts[1])
    new_status = int(parts[2])
    
    async with rq.engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO premium_events_status (chat_id, is_active) 
            VALUES (:chat_id, :status)
            ON CONFLICT(chat_id) DO UPDATE SET is_active = :status
        """), {'chat_id': chat_id, 'status': new_status})
            
    await render_events_menu(bot, chat_id, callback.from_user.id, callback.message)


@router.callback_query(F.data.startswith('edit_events_menu_'), flags=flag_default)
async def callback_edit_events_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = int(callback.data.split('_')[3])
    
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить событие ➕", callback_data=f'set_event_{chat_id}')],
        [InlineKeyboardButton(text="Удалить событие ➖", callback_data=f'del_event_menu_{chat_id}')],
        [InlineKeyboardButton(text="Очистить список 🗑", callback_data=f'clear_events_confirm_{chat_id}')],
        [InlineKeyboardButton(text="Назад ↩", callback_data=f'prem_events_{chat_id}')]
    ])
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>✏️ Изменение списка случайных событий. Выберите нужное действие:</b>",
        reply_markup=kb_edit,
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith('set_event_'), flags=flag_default)
async def callback_set_event_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_id = callback.data.split('_')[2]
    await state.set_state(SetLists.event_type)
    await state.update_data(set_chat_id=chat_id)
    
    kb_type = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Текстовое (без игроков)", callback_data="EventType_0")],
        [InlineKeyboardButton(text="С участием 1 игрока", callback_data="EventType_1")],
        [InlineKeyboardButton(text="С участием 2 игроков", callback_data="EventType_2")],
        [InlineKeyboardButton(text="Отмена 🚫", callback_data=f'edit_events_menu_{chat_id}')]
    ])
    
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>Выберите тип случайного события:</b>\n\n"
             "<i>Текстовое</i> — просто описание ситуации (например: <code>Сломался генератор, в бункере темно.</code>)\n\n"
             "<i>С 1 игроком</i> — случайный игрок будет подставлен в текст. Используйте тег <b>[Игрок]</b>.\n\n"
             "<i>С 2 игроками</i> — два случайных игрока. Используйте теги <b>[Игрок1]</b> и <b>[Игрок2]</b>.",
        reply_markup=kb_type,
        parse_mode='HTML'
    )


@router.callback_query(F.data.startswith('EventType_'), flags=flag_default)
async def callback_event_type_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    event_type = int(callback.data.split('_')[1])
    await state.update_data(event_type=event_type)
    await state.set_state(SetLists.event_text)
    
    data = await state.get_data()
    chat_id = data['set_chat_id']
    
    if event_type == 0:
        example = "Вентиляция вышла из строя на 2 часа."
    elif event_type == 1:
        example = "[Игрок] случайно разбил банку с консервами."
    else:
        example = "[Игрок1] и [Игрок2] подрались из-за последнего куска хлеба."
        
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>Отправьте текст события.</b>\n\n"
             f"📝 Пример:\n<code>{example}</code>\n\n"
             "🚫 Учтите, нельзя использовать символы:\n"
             f"  [ _ ]    [ / ]    [ &lt; ]    [ &gt; ]    [ \" ]    [ ' ]    [ + ]",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена 🚫", callback_data=f'edit_events_menu_{chat_id}')]]),
        parse_mode='HTML'
    )


@router.message(StateFilter(SetLists.event_text))
async def msg_event_text_receive(message: Message, state: FSMContext):
    if not message.text or message.text.startswith('/'): return
    
    if any(char in message.text for char in ['_', '/', '<', '>', "'", '"', '+']):
        await retry_after_decorate(message.answer)(
            text="<b>🚫 Нельзя использовать спецсимволы. Отправьте текст снова.</b>", parse_mode='HTML')
        return
        
    data = await state.get_data()
    event_type = data['event_type']
    text_val = message.text.strip()
    
    if event_type == 1 and "[игрок]" not in text_val.lower():
        await retry_after_decorate(message.answer)("<b>❌ В тексте отсутствует тег [Игрок]. Отправьте текст заново.</b>", parse_mode='HTML')
        return
    if event_type == 2 and ("[игрок1]" not in text_val.lower() or "[игрок2]" not in text_val.lower()):
        await retry_after_decorate(message.answer)("<b>❌ В тексте отсутствуют теги [Игрок1] и/или [Игрок2]. Отправьте текст заново.</b>", parse_mode='HTML')
        return
        
    await state.update_data(event_text=text_val)
    
    kb_confirm = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить ✅", callback_data=f"add_event_confirm")],
        [InlineKeyboardButton(text="Отмена 🚫", callback_data=f"edit_events_menu_{data['set_chat_id']}")]
    ])
    
    await retry_after_decorate(message.answer)(
        text=f"<b>❔ Добавить это событие?</b>\n\n<code>{html.escape(text_val)}</code>",
        reply_markup=kb_confirm,
        parse_mode='HTML'
    )


@router.callback_query(F.data == 'add_event_confirm', flags=flag_default)
async def callback_add_event_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    chat_id = int(data['set_chat_id'])
    event_type = data['event_type']
    event_text = data['event_text']
    
    async with rq.engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO premium_events (chat_id, event_type, event_text) VALUES (:c, :typ, :txt)"),
            {'c': chat_id, 'typ': event_type, 'txt': event_text}
        )
        
    await callback.message.delete()
    await retry_after_decorate(bot.send_message)(chat_id=callback.from_user.id, text="<b>✅ Событие успешно добавлено!</b>", parse_mode='HTML')
    await state.set_state(None)
    await render_events_menu(bot, chat_id, callback.from_user.id)


@router.callback_query(F.data.startswith('del_event_menu_'), flags=flag_default)
async def callback_del_event_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_id = int(callback.data.split('_')[3])
    
    await state.set_state(SetLists.event_delete)
    await state.update_data(set_chat_id=chat_id)
    
    kb_back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена 🚫", callback_data=f'edit_events_menu_{chat_id}')]])
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>➖ Отправьте мне ID события, которое нужно удалить (номер можно посмотреть в главном меню списка).</b>",
        reply_markup=kb_back, parse_mode='HTML'
    )


@router.message(StateFilter(SetLists.event_delete))
async def msg_event_delete_receive(message: Message, state: FSMContext, bot: Bot):
    if not message.text or message.text.startswith('/'): return
    
    data = await state.get_data()
    chat_id = int(data['set_chat_id'])
    
    if not message.text.isdigit():
        await message.answer("<b>❌ ID должен быть числом! Попробуйте еще раз.</b>", parse_mode='HTML')
        return
        
    event_id = int(message.text)
    
    async with rq.engine.begin() as conn:
        res = await conn.scalar(text("SELECT id FROM premium_events WHERE id = :id AND chat_id = :chat_id"), {'id': event_id, 'chat_id': chat_id})
        if res:
            await conn.execute(text("DELETE FROM premium_events WHERE id = :id AND chat_id = :chat_id"), {'id': event_id, 'chat_id': chat_id})
            await message.answer(f"<b>✅ Событие с ID {event_id} успешно удалено!</b>", parse_mode='HTML')
        else:
            await message.answer(f"<b>❌ Событие с ID {event_id} не найдено в вашем списке.</b>", parse_mode='HTML')
    
    await state.set_state(None)
    await render_events_menu(bot, chat_id, message.from_user.id)


@router.callback_query(F.data.startswith('clear_events_confirm_'), flags=flag_default)
async def callback_clear_events_confirm(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.data.split('_')[3]
    kb_clear = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, удалить всё 🗑", callback_data=f"clear_all_events_{chat_id}")],
        [InlineKeyboardButton(text="Отмена 🚫", callback_data=f'edit_events_menu_{chat_id}')]
    ])
    await callback.message.edit_text("<b>Вы уверены, что хотите удалить ВСЕ свои события?</b>", reply_markup=kb_clear, parse_mode='HTML')


@router.callback_query(F.data.startswith('clear_all_events_'), flags=flag_default)
async def callback_clear_all_events(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    chat_id = int(callback.data.split('_')[3])
    async with rq.engine.begin() as conn:
        await conn.execute(text("DELETE FROM premium_events WHERE chat_id = :chat_id"), {'chat_id': chat_id})
        await conn.execute(text("UPDATE premium_events_status SET is_active = 0 WHERE chat_id = :chat_id"), {'chat_id': chat_id})
        
    await callback.message.delete()
    await retry_after_decorate(bot.send_message)(chat_id=callback.from_user.id, text="<b>✅ Список очищен!</b>", parse_mode='HTML')
    await render_events_menu(bot, chat_id, callback.from_user.id)


@router.message(Command(query), F.from_user.id == admin_id, flags=flag_default)
async def cmd_sql_query_start(message: Message, state: FSMContext):
    parts = message.text.split(query_split)
    if len(parts) < 3:
        await message.answer("Неверный формат команды для SQL запроса.")
        return
        
    query_text = parts[1]
    query_type = parts[2]
    
    if query_type not in ['commit', 'select']:
        await message.answer('Укажите тип запроса [commit / select]')
        return
        
    await state.set_state(SqlState.sql_text)
    await state.update_data(sql_text=query_text)
    await message.answer('Вы уверены, что хотите выполнить запрос:\n\n'
                         '```SQL\n'
                         f'{query_text}```', parse_mode='Markdown',
                         reply_markup=await kb.sql_query(query_type))

@router.callback_query(F.data == 'sqlNo', SqlState.sql_text)
async def callback_sql_query_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()

@router.callback_query(F.data.startswith(query), SqlState.sql_text)
async def callback_sql_query_execute(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.clear()
    
    query_type = callback.data.split('_')[2]
    sql_text = await rq.sql_query(query_type, data['sql_text'])
    
    if sql_text == 'commit':
        await callback.message.edit_text(text='ИЗМЕНЕНИЯ СОХРАНЕНЫ')
    else:
        result_str = str(sql_text)
        if len(result_str) > 4096:
            for x in range(0, len(result_str), 4000):
                await callback.message.edit_text(text=result_str[x:x + 4000])
        else:
            await callback.message.edit_text(text=f'{result_str}')