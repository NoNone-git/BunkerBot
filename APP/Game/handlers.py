import asyncio
import html
import random
import aiogram.exceptions
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State

import APP.Game.keyboards as kb
import APP.Game.requests as rq
import APP.Game.func as gf
from config import user_state, rooms, error_chat_id, bot_id, admin_id
from APP.Game.func import PlayerState
from APP.Game.Classes import Room
from APP.BaseFunc.requests import select_chat_settings, select_prem_settings
from APP.Middlewares.decorators import retry_after_decorate, retry_bad_decorate
from APP.Middlewares.throttling_middleware import ThrottlingMiddleware, flag_default
from APP.BaseFunc.settings import Settings, PremiumSettings
from APP.BaseFunc.updates_requests import set_chat

# Импортируем наш глобальный словарь для быстрого перевода
from APP.Game.requests import CHAR_INFO_RU

router = Router()
router.callback_query.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                                      throttle_time_end=4, throttle_time_other=0.2,
                                                      throttle_time_card=4))
router.message.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                               throttle_time_end=4, throttle_time_other=0.2,
                                               throttle_time_card=4))


class StopGame(StatesGroup):
    chat_stop = State()


########################################################################################################################
#                                                       СТАРТ                                                          #
########################################################################################################################


@router.message(F.from_user.id != F.chat.id, F.chat.id.in_(rooms), Command(commands=['stop_game']), flags=flag_default)
async def cmd_stop_game(message: Message, bot: Bot):
    state = await user_state(message.from_user.id, bot.id)
    data = await state.get_data()
    room = rooms[message.chat.id]
    settings: Settings = room.settings
    
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state != 'start_register':
        if settings.stop_game == 'Votes' and (room.chat_id == data.get('chat_id') or status in ('administrator', 'creator')):
            await retry_after_decorate(message.answer)(
                text="<b><blockquote>❕—— ЗАВЕРШИТЬ ИГРУ? ——❕</blockquote>\n\n"
                     "Проголосуйте, если хотите завершить игру</b>",
                parse_mode='HTML',
                reply_markup=await kb.stop_game(room.chat_id, len(room.stop_game)))
                
        if settings.stop_game == 'Admins' and status in ('administrator', 'creator'):
            await room.close_room(bot=bot)
            await retry_after_decorate(message.answer)(
                text='<b>✅ Игра завершена</b>',
                parse_mode='HTML')
    else:
        await retry_after_decorate(message.answer)(
            text='<b>💢 Игра еще не началась\n\n'
                 'Bы можете отменить регистрацию командой\n/stop_register</b>',
            parse_mode='HTML')


@router.message(F.from_user.id != F.chat.id, F.chat.id.in_(rooms), Command(commands=['stop_register']), flags=flag_default)
async def cmd_stop_register(message: Message, bot: Bot):
    room: Room = rooms[message.chat.id]
    settings: Settings = room.settings
    
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state == 'start_register':
        if (settings.stop_register == 'StartPlayer' and (room.user_start_id == message.from_user.id or status in ('administrator', 'creator'))) or \
           (settings.stop_register == 'Admins' and status in ('administrator', 'creator')):
            
            if room.round_msg:
                await retry_bad_decorate(bot.delete_messages)(chat_id=message.chat.id, message_ids=room.round_msg)
            await room.close_room(bot=bot)
            await retry_after_decorate(message.answer)(text='<i><b>☑️ Регистрация отменена</b></i>', parse_mode='HTML')
            try:
                await message.delete()
            except aiogram.exceptions.TelegramBadRequest:
                pass


@router.message(F.from_user.id != F.chat.id, F.chat.id.in_(rooms), Command(commands=['extend_register']), flags=flag_default)
async def cmd_extend_register_timer(message: Message, bot: Bot):
    room: Room = rooms[message.chat.id]
    settings: Settings = room.settings
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state == 'start_register':
        if (settings.extend_register == 'StartPlayer' and (room.user_start_id == message.from_user.id or status in ('administrator', 'creator'))) or \
           (settings.extend_register == 'Admins' and status in ('administrator', 'creator')):
            
            args = message.text.split()
            added_time = int(args[1]) if len(args) == 2 and args[1].isdigit() else 30
            room.timer += added_time
            await retry_after_decorate(message.answer)(
                text=f'<i><b>☑️ Регистрация продлена на {added_time} сек</b></i>', parse_mode='HTML')


@router.message(F.from_user.id != F.chat.id, F.chat.id.in_(rooms), Command(commands=['extend']), flags=flag_default)
async def cmd_extend_disable_timer(message: Message, bot: Bot):
    room: Room = rooms[message.chat.id]
    settings: Settings = room.settings
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state == 'start_register':
        if (settings.extend_register == 'StartPlayer' and (room.user_start_id == message.from_user.id or status in ('administrator', 'creator'))) or \
           (settings.extend_register == 'Admins' and status in ('administrator', 'creator')):
            
            room.extend = 'Yes'
            await retry_after_decorate(message.answer)(
                text='<i><b>☑️ Таймер до начала игры отключен.\nДля запуска игры используйте команду /start</b></i>',
                parse_mode='HTML')


@router.message(F.from_user.id != F.chat.id,  F.chat.id.in_(rooms), Command(commands=['extend_discussion']), flags=flag_default)
async def cmd_extend_discussion_timer(message: Message, bot: Bot):
    room: Room = rooms[message.chat.id]
    settings: Settings = room.settings
    state = await user_state(user_id=message.from_user.id, bot_id=bot.id)
    data = await state.get_data()
    
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state == 'start_discussion':
        if (settings.extend_discussion == 'Players' and (room.chat_id == data.get('chat_id') or status in ('administrator', 'creator'))) or \
           (settings.extend_discussion == 'Admins' and status in ('administrator', 'creator')):
            
            args = message.text.split()
            added_time = int(args[1]) if len(args) == 2 and args[1].isdigit() else 30
            room.timer += added_time
            await retry_after_decorate(message.answer)(
                text=f'<i><b>☑️  Обсуждение продлено на {added_time} сек</b></i>', parse_mode='HTML')


@router.message(F.from_user.id != F.chat.id, F.chat.id.in_(rooms), Command(commands=['start']), flags=flag_default)
async def cmd_start_game(message: Message, bot: Bot):
    room: Room = rooms[message.chat.id]
    settings: Settings = room.settings
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if room.state == 'start_register':
        if (settings.start_game == 'Users' and (room.user_start_id == message.from_user.id or status in ('administrator', 'creator'))) or \
           (settings.start_game == 'Admins' and status in ('administrator', 'creator')):
            
            if room.players < settings.min_players:
                await retry_after_decorate(message.answer)(
                    text='<b><blockquote>❕—— ОШИБКА ЗАПУСКА ——❕</blockquote>\n\n'
                         'Вы не можете досрочно начать игру, недостаточно игроков\n \n'
                         f'<i>Минимальное количество игроков в этом чате: {settings.min_players}</i></b>',
                    parse_mode='HTML')
            else:
                room.state = "stop_register"
                if room.round_msg:
                    await bot.delete_messages(message.chat.id, room.round_msg)
                await asyncio.sleep(2)
                await gf.start_game(room, bot, message)


########################################################################################################################
#                                 ГОЛОСОВАНИЕ: ДОЛЖЕН ВЫЛЕТЕТЬ 1 УЧАСТНИК                                              #
########################################################################################################################


@router.callback_query(F.data.startswith('GroupVoice_'), PlayerState.in_game, flags=flag_default)
async def callback_group_voice_select(callback: CallbackQuery):
    parts = callback.data.split('_')
    target_id = parts[1]
    not_votes = parts[2]
    
    if target_id != 'skip':
        user_info = await rq.get_user_info(target_id)
        player_info = await rq.get_player_by_id(user_id=target_id)
        open_player_info = [x for x in player_info if x and str(x).startswith('open_')]
        
        message_result = f'<b><i>🧩 Информация о игроке {html.escape(user_info[2])}:\n\n<blockquote expandable>'
        for line in open_player_info:
            line_parts = line.split('_')
            if len(line_parts) >= 4:
                message_result += f'{line_parts[1]}: {line_parts[3]}\n'
                
        await retry_after_decorate(callback.message.edit_text)(
            text=f'{message_result}</blockquote>\nВы уверены, что хотите проголосовать  '
                 f'против [{user_info[1]}] {html.escape(user_info[2])}?</i></b>',
            parse_mode='HTML',
            reply_markup=await kb.group_voice_for_player_yes_or_no(target_id, not_votes))
    else:
        await retry_after_decorate(callback.message.edit_text)(
            text='❎ Вы уверены, что хотите не выгонять никого в этом раунде?',
            parse_mode='HTML',
            reply_markup=await kb.group_voice_for_player_yes_or_no(target_id, not_votes))


@router.callback_query(F.data.startswith('GrVoice_'), PlayerState.in_game, flags=flag_default)
async def callback_group_voice_reselect(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    room: Room = rooms[data['chat_id']]
    
    if 'voice' in data or room.state == 'stop_votes':
        pass
    else:
        not_votes = callback.data.split('_')[1]
        await retry_after_decorate(callback.message.edit_text)(
            text='🛑 Выберите игрока, которого хотите выгнать.',
            reply_markup=await kb.group_player_voice(data['chat_id'], callback.from_user.id, not_votes))


########################################################################################################################
#                                                      СТАТИСТИКА                                                      #
########################################################################################################################


@router.callback_query(F.data == 'cataclysm', PlayerState.in_game, flags=flag_default)
async def callback_cataclysm_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    room: Room = rooms[data['chat_id']]
    
    cataclysm_data = room.bunker.get('cataclysm', '')
    parts = cataclysm_data.split('+')
    title = parts[0] if len(parts) > 0 else 'Неизвестно'
    desc = parts[1] if len(parts) > 1 else 'Нет описания'
    
    await callback.message.edit_text(
        text=f"⚠️ Информация о катастрофе:\n\n{title}\n\n{desc}",
        reply_markup=kb.back_game_info, parse_mode='HTML')


@router.callback_query(F.data == 'events', PlayerState.in_game, flags=flag_default)
async def callback_events_info(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    room: Room = rooms[data['chat_id']]
    
    if room.events_text:
        events_text = '\n\n'.join([f"• {event}" for event in room.events_text])
        text = f'<b>🎲 Случайные события произошедшие в течении этой игры:\n \n<blockquote expandable>{events_text}</blockquote></b>'
    else:
        text = '<b>❌ В этой игре ещё не происходило событий!</b>'
        
    await callback.message.edit_text(text=text, parse_mode='HTML', reply_markup=kb.back_game_info)


@router.callback_query(F.data == 'game_info', PlayerState.in_game, flags=flag_default)
async def callback_game_info(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    player_info = await rq.get_player_by_id(callback.from_user.id)
    card1 = await rq.get_player_card(callback.from_user.id)
    
    def get_val(item): return str(item).split('_')[-1] if item else 'Неизвестно'
    
    card_parts = card1.split('_') if card1 else []
    card_desc = await rq.get_card(f"{card_parts[-2]}_{card_parts[-1]}") if len(card_parts) >= 2 else "Нет карты"
    
    text = (f'⚠️ Катастрофа: <b><i><u>{get_val(player_info[6])}</u></i></b>\n \n'
            f'♦️ <b>Ваши характеристики:</b>\n \n'
            f'<blockquote>💼 Профессия: {get_val(player_info[0])}</blockquote>\n'
            f'<blockquote>👤 Био информация: {get_val(player_info[1])}</blockquote>\n'
            f'<blockquote>🫀 Здоровье: {get_val(player_info[2])}</blockquote>\n'
            f'<blockquote>🧩 Хобби: {get_val(player_info[3])}</blockquote>\n'
            f'<blockquote>🎒 Багаж: {get_val(player_info[4])}</blockquote>\n'
            f'<blockquote>✳ Доп. информация: {get_val(player_info[5])}</blockquote>\n'
            f'<blockquote>🕷 Фобия: {get_val(player_info[7])}</blockquote>\n'
            f'<blockquote>💊 Зависимость: {get_val(player_info[8])}</blockquote>\n'
            f'<blockquote>😎 Черта характера: {get_val(player_info[9])}</blockquote>\n \n'
            f'<blockquote>🃏 Карта действия №1: {card_desc}</blockquote>')
            
    await callback.message.edit_text(
        text=text,
        reply_markup=await kb.play_info(card1 if card1 and not card1.startswith('open_') else None),
        parse_mode='HTML')


@router.callback_query(F.data.startswith('stop_'), F.message.chat.id.in_(rooms), flags=flag_default)
async def callback_stop_game_votes(callback: CallbackQuery, bot: Bot):
    state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
    room: Room = rooms[callback.message.chat.id]
    
    try:
        status = (await bot.get_chat_member(user_id=callback.from_user.id, chat_id=callback.message.chat.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if status in ('creator', 'administrator'):
        await callback.answer('')
        await room.close_room(bot=bot)
        await retry_after_decorate(callback.message.edit_text)(
            text='<b>⌛️ Игра завершается...\nНовую игру можно запустить через 30 сек.</b>',
            parse_mode='HTML')
            
        chat_state: FSMContext = await user_state(callback.message.chat.id, bot.id)
        await chat_state.set_state(StopGame.chat_stop)
        await asyncio.sleep(30)
        await chat_state.clear()
        
        await retry_after_decorate(callback.message.answer)(text='<b>✅ Игра завершена</b>', parse_mode='HTML')
        await retry_after_decorate(bot.send_message)(
            chat_id=error_chat_id,
            text=f'🟢 Игра завершена по кнопке 🟢\n{callback.message.chat.username}\n{callback.message.from_user.username}')
    else:
        data = await state.get_data()
        if data.get('chat_id') == callback.message.chat.id:
            if callback.from_user.id in room.stop_game:
                await callback.answer('Голос уже учтен!')
            elif len(room.stop_game) == 2:
                await callback.answer()
                await room.close_room(bot=bot)
                await retry_after_decorate(callback.message.edit_text)(
                    text='<b>⌛️ Игра завершается...\nНовую игру можно запустить через 30 сек.</b>',
                    parse_mode='HTML')
                    
                chat_state: FSMContext = await user_state(callback.message.chat.id, bot.id)
                await chat_state.set_state(StopGame.chat_stop)
                await asyncio.sleep(30)
                await chat_state.clear()
                
                await retry_after_decorate(callback.message.answer)(text='<b>✅ Игра завершена</b>', parse_mode='HTML')
                await retry_after_decorate(bot.send_message)(
                    chat_id=error_chat_id,
                    text=f'🟢 Игра завершена по кнопке 🟢\n{callback.message.chat.username}\n{callback.message.from_user.username}')
            elif len(room.stop_game) < 2:
                room.stop_game.append(callback.from_user.id)
                await retry_after_decorate(callback.message.edit_reply_markup)(
                    reply_markup=await kb.stop_game(room.chat_id, len(room.stop_game)))
                await callback.answer('Голос учтён!')
        else:
            await callback.answer('Вы не участник этой игры!')


@router.callback_query(F.data == 'bunker_info', PlayerState.in_game, flags=flag_default)
async def callback_bunker_info(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    room = rooms[data['chat_id']]
    await callback.answer('')
    
    rooms_list = room.bunker.get('rooms', [])
    room_text = ', '.join(rooms_list)
    location = room.bunker.get('location', 'Неизвестно')
    supplies = room.bunker.get('supplies', ['-', '-'])
    sup1 = supplies[0] if len(supplies) > 0 else '-'
    sup2 = supplies[1] if len(supplies) > 1 else '-'
    
    text = (f"Информация о бункере:\n\n"
            f"🏕 Бункер находится {location}\n\n"
            f"🧳 В бункере есть:\n{sup1}, {sup2}\n\n"
            f"⚠️ Спец. комнаты:\n{room_text}\n\n"
            f"👤 Мест в бункере: {gf.user_win_table[room.players - 4]}\n\n")
            
    await callback.message.edit_text(text=text, reply_markup=kb.back_game_info)


@router.message(F.from_user.id != F.chat.id, ~StateFilter(StopGame.chat_stop), Command(commands=['game']), flags=flag_default)
async def cmd_game_start(message: Message, bot: Bot):
    chat_state: FSMContext = await user_state(message.chat.id, bot.id)
    if message.chat.id in rooms or await chat_state.get_state() == StopGame.chat_stop:
        await retry_after_decorate(message.answer)(
            text='<i><b><blockquote>❕—— ОШИБКА ЗАПУСКА ——❕</blockquote>\n'
                 '💢 Дождитесь завершения активной игры</b></i>',
            parse_mode='HTML')
        return
        
    chat_members = await bot.get_chat_member_count(message.chat.id)
    await set_chat(message.chat.id, message.chat.full_name, chat_members, message.chat.username)
    
    try:
        bot_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=bot.id)
        bot_status = bot_member.status
        # Безопасное получение прав для администраторов и создателей
        if bot_status == 'creator':
            can_pin = True
            can_del = True
        else:
            can_pin = getattr(bot_member, 'can_pin_messages', False)
            can_del = getattr(bot_member, 'can_delete_messages', False)
    except aiogram.exceptions.TelegramAPIError:
        bot_status = 'member'
        can_pin = False
        can_del = False
        
    if bot_status not in ('administrator', 'creator') or not can_pin or not can_del:
        await retry_after_decorate(message.answer)(
            text='<i><b><blockquote>❕—— ОШИБКА ДОСТУПА ——❕</blockquote>\n'
                 '💢 Я не могу начать игру, пока мне не выданы следующие права:\n\n'
                 ' - Закреплять сообщения\n'
                 ' - Удалять сообщения</b></i>',
            parse_mode='HTML')
        return
        
    settings: Settings = Settings(await select_chat_settings(message.chat.id))
    try:
        status = (await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)).status
    except aiogram.exceptions.TelegramAPIError:
        status = 'member'
        
    if settings.start_game == 'Users' or (settings.start_game == 'Admins' and status in ('administrator', 'creator')):
        msg_start = await retry_after_decorate(message.answer)(
            text='<b>Ведется набор в игру</b>',
            reply_markup=await kb.invite_bot_link(message.chat.id), parse_mode='HTML')
        msg = msg_start.message_id
        
        if settings.pin_reg_msg:
            try:
                await retry_after_decorate(msg_start.pin)(disable_notification=True)
            except aiogram.exceptions.TelegramBadRequest:
                pass
                
        chat_status = await rq.get_chat_status(message.chat.id)
        if chat_status == 'premium':
            ddd = await select_prem_settings(message.chat.id)
            prem_settings = PremiumSettings(ddd)
        else:
            prem_settings = PremiumSettings()
            
        room: Room = Room(chat_id=message.chat.id, settings=settings, start_msg_id=msg, user_start=message.from_user.id,
                          prem_settings=prem_settings)
        rooms[message.chat.id] = room
        room.round_msg.append(msg)
        
        await asyncio.sleep(30)
        while room.timer > 0 and room.extend == 'No':
            if message.chat.id in rooms and room.state == "start_register":
                if room.timer % 30 != 0:
                    await asyncio.sleep(room.timer - (room.timer // 30) * 30)
                    room.timer -= room.timer - (room.timer // 30) * 30
                    
                msg1 = (await retry_after_decorate(message.answer)(
                    text=f'<i><b>До завершения регистрации участников {room.timer} сек</b></i>',
                    reply_markup=await kb.invite_bot_link(message.chat.id), reply_to_message_id=msg_start.message_id,
                    parse_mode='HTML', allow_sending_without_reply=True)).message_id
                room.round_msg.append(msg1)
                
                await asyncio.sleep(30)
                room.timer -= 30
            else:
                return
                
        if room.extend == 'Yes':
            return
            
        if message.chat.id in rooms and room.state == "start_register":
            room.state = "stop_register"
            if room.round_msg:
                await bot.delete_messages(chat_id=message.chat.id, message_ids=room.round_msg)
            await asyncio.sleep(2)
            
            if room.players < settings.min_players:
                await retry_after_decorate(message.answer)(
                    text='<b><blockquote>❕—— ОШИБКА ЗАПУСКА ——❕</blockquote>\n\n'
                         f'<i>Минимальное количество игроков в этом чате: {settings.min_players}</i></b>',
                    parse_mode='HTML')
                await room.close_room(bot=bot)
            else:
                room.state = "stop_register"
                await asyncio.sleep(2)
                await gf.start_game(room, bot, message)


@router.callback_query(F.data.startswith('AdmStopD_'), F.message.chat.id.in_(rooms))
async def callback_adm_stop_discussion(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    try:
        status = (await bot.get_chat_member(user_id=callback.from_user.id, chat_id=callback.message.chat.id)).status
    except aiogram.exceptions.TelegramAPIError:
        return
        
    if status not in ('administrator', 'creator'):
        return
        
    room: Room = rooms[callback.message.chat.id]
    await room.set_votes_count()
    room.state = "stop_discussion"
    room.time_discussion = 1
    
    try:
        await callback.message.delete()
    except aiogram.exceptions.TelegramBadRequest:
        pass
        
    if room.number_votes in (1, 0):
        await gf.one_votes(room, bot, callback.message)
    elif room.number_votes == 2:
        await gf.two_votes(room, callback.message, bot, 'первого', room.round)


@router.callback_query(F.data.startswith('StopD_'), F.message.chat.id.in_(rooms))
async def callback_stop_discussion(callback: CallbackQuery, bot: Bot):
    room: Room = rooms[callback.message.chat.id]
    if room.state == "start_discussion":
        state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
        if await state.get_state() != PlayerState.in_game:
            return
            
        if callback.from_user.id not in room.stop_discussion:
            parts = callback.data.split('_')
            max_votes = int(parts[2])
            
            if len(room.stop_discussion) == max_votes - 1:
                await room.set_votes_count()
                room.state = "stop_discussion"
                room.time_discussion = 1
                try:
                    await callback.message.delete()
                except aiogram.exceptions.TelegramBadRequest:
                    pass
                    
                if room.number_votes in (1, 0):
                    await gf.one_votes(room, bot, callback.message)
                elif room.number_votes == 2:
                    await gf.two_votes(room, callback.message, bot, 'первого', room.round)
            else:
                if callback.from_user.id in room.next_round:
                    room.next_round.remove(callback.from_user.id)
                room.stop_discussion.append(callback.from_user.id)
                
                reply_markup = (await kb.stop_discussion(len(room.stop_discussion), parts[2], parts[3], room.settings.stop_discussion) 
                                if len(parts) == 4 else 
                                await kb.next_round(len(room.stop_discussion), parts[2], parts[3], len(room.next_round), room.settings.next_round, room.settings.stop_discussion))
                                
                await retry_after_decorate(callback.message.edit_reply_markup)(reply_markup=reply_markup)
                await callback.answer('Голос учтён')
        else:
            await callback.answer('Ваш голос уже учтён')


@router.callback_query(F.data.startswith('AdmNextR_'), F.message.chat.id.in_(rooms))
async def callback_adm_next_round(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    try:
        status = (await bot.get_chat_member(user_id=callback.from_user.id, chat_id=callback.message.chat.id)).status
    except aiogram.exceptions.TelegramAPIError:
        return
        
    if status not in ('administrator', 'creator'):
        return
        
    room: Room = rooms[callback.message.chat.id]
    await room.set_votes_count()
    room.state = "stop_discussion"
    room.time_discussion = 1
    
    try:
        await callback.message.delete()
    except aiogram.exceptions.TelegramBadRequest:
        pass
        
    await gf.new_round(room, bot, callback.message)


@router.callback_query(F.data.startswith('NextR_'), F.message.chat.id.in_(rooms), flags=flag_default)
async def callback_next_round(callback: CallbackQuery, bot: Bot):
    room: Room = rooms[callback.message.chat.id]
    if room.state == "start_discussion":
        state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
        if await state.get_state() != PlayerState.in_game:
            return
            
        if callback.from_user.id not in room.next_round:
            parts = callback.data.split('_')
            max_votes = int(parts[2])
            
            if len(room.next_round) == max_votes - 1:
                await room.set_votes_count()
                room.state = "stop_discussion"
                room.time_discussion = 1
                try:
                    await callback.message.delete()
                except aiogram.exceptions.TelegramBadRequest:
                    pass
                await gf.new_round(room, bot, callback.message)
            else:
                if callback.from_user.id in room.stop_discussion:
                    room.stop_discussion.remove(callback.from_user.id)
                room.next_round.append(callback.from_user.id)
                
                await retry_after_decorate(callback.message.edit_reply_markup)(
                    reply_markup=await kb.next_round(len(room.stop_discussion), parts[2], parts[3], len(room.next_round), room.settings.next_round, room.settings.stop_discussion))
                await callback.answer('Голос учтён')
        else:
            await callback.answer('Ваш голос уже учтён')


@router.callback_query(F.data.startswith('GrYesVoice_'), PlayerState.in_game, flags=flag_default)
async def callback_gr_yes_voice(callback: CallbackQuery, bot: Bot, state: FSMContext):
    player_info = await rq.get_user_info(callback.from_user.id)
    room: Room = rooms[(await state.get_data())['chat_id']]
    
    if room.players_dict[callback.from_user.id]['voice'] == 0 and room.state != 'stop_votes':
        parts = callback.data.split('_')
        target_id = parts[1]
        not_votes = parts[2]
        
        if target_id != 'skip':
            user_info = await rq.get_user_info(target_id)
            await rq.voice_for_player(target_id, player_info[1], callback.from_user.id)
            room.players_dict[callback.from_user.id]['voice'] = 1
            text_votes = f'✅ <b>Вы проголосовали против [{user_info[1]}] {html.escape(user_info[2])}.</b>'
        else:
            text_votes = '✅ <b>Вы проголосовали за то, чтоб никого не выгонять в этом раунде.</b>'
            await rq.player_skip_voice(callback.from_user.id)
            room.players_dict[callback.from_user.id]['voice'] = 1
            
        text = f'👉 <b><i><u>НАЧАЛО ГОЛОСОВАНИЯ</u> 👈\n\n<blockquote>'
        users = await rq.get_active_players_emoji(player_info[0])
        users.sort()
        
        for user in users:
            # Безопасное форматирование без вложенных кавычек
            vote_val = '0' if user[2] is None else (user[4] if room.settings.anonymous_votes else user[2])
            text += f'[{user[1]}] <a href="tg://user?id={user[3]}">{html.escape(user[0])}</a>: {vote_val}\n'
            
        text += '</blockquote></i></b>'
        
        if int(not_votes) == 0:
            skip = await rq.get_skip_votes_players(room.chat_id)
            skip_val = skip[0] if not room.settings.anonymous_votes else skip[1]
            text += f'\n<b><i>❎  Скип: {skip_val}\n\n👌 В этом раунде голосование можно пропустить</i></b>'
            
        msg_chat = await retry_bad_decorate(bot.edit_message_text)(
            chat_id=room.chat_id, message_id=room.votes_msg_id, text=text,
            reply_markup=kb.bot_link_votes, parse_mode="HTML")
            
        await retry_after_decorate(callback.message.edit_text)(
            text=text_votes, reply_markup=await kb.link_chat(room.chat_id, room.votes_msg_id), parse_mode="HTML")
            
        res = await rq.select_votes_players(room.chat_id)
        if room.state == 'stop_votes':
            return False
            
        if 0 not in res:
            if room.state == 'one_votes':
                room.time_votes = 1
                room.state = "stop_votes"
                await gf.finish_one_votes(msg_chat, bot, room)
            elif room.state == 'first_two_votes':
                room.time_votes = 1
                room.state = "stop_votes"
                await gf.finish_two_votes(room, msg_chat, bot, 'первого')
            elif room.state == 'second_two_votes':
                room.time_two_votes = 1
                room.state = "stop_votes"
                await gf.finish_two_votes(room, msg_chat, bot, 'второго')


@router.callback_query(F.data.startswith('GrOpen_'), PlayerState.in_game, flags=flag_default)
async def callback_group_open_char(callback: CallbackQuery, bot: Bot, state: FSMContext):
    room: Room = rooms[(await state.get_data())['chat_id']]
    user_info = await rq.get_user_info(callback.from_user.id)
    
    if room.state not in ('stop_open', 'start_discussion') and room.players_dict[callback.from_user.id]['open'] == 0:
        char_type = callback.data.split('_')[1]
        result = CHAR_INFO_RU.get(char_type, '🫀 Здоровье')
        
        char_result_str = await rq.select_char_by_name(callback.from_user.id, char_type)
        char_result = char_result_str.split('_')[-1] if char_result_str else 'Неизвестно'
        
        await rq.update_characteristics(callback.from_user.id, char_type)
        room.players_dict[callback.from_user.id]['open'] = 1
        
        msg = await retry_bad_decorate(bot.send_message)(
            chat_id=room.chat_id,
            text=f'<b>[{user_info[1]}] <a href="tg://user?id={user_info[3]}">{html.escape(user_info[2])}</a>:\n\n{result}: {char_result}</b>',
            parse_mode="HTML")
        room.round_msg.append(msg.message_id)
        
        await retry_after_decorate(callback.message.edit_text)(
            text=f'<b>✅ Вы открыли характеристику:\n \n{result}: {char_result}\n \nПерейдите в чат для обсуждения</b>',
            message=callback.message,
            reply_markup=await kb.link_chat(room.chat_id, msg.message_id), parse_mode="HTML")
            
        if room.state in ('stop_open', 'start_discussion'):
            return
            
        res = await rq.select_open_characteristics_in_room(user_info[0])
        if 0 not in res:
            room.state = "start_discussion"
            await room.set_votes_count()
            await gf.votes_start(bot, msg, room)


@router.callback_query(F.data == 'BotOpen', flags=flag_default)
async def callback_bot_open_char(callback: CallbackQuery, bot: Bot):
    await callback.answer('')
    state = await user_state(user_id=callback.from_user.id, bot_id=bot.id)
    if await state.get_state() != PlayerState.in_game:
        return
        
    room: Room = rooms[(await state.get_data())['chat_id']]
    user_info = await rq.get_user_info(callback.from_user.id)
    info_player = await rq.get_player_by_id(callback.from_user.id)
    
    close_player_info = [x for x in info_player if x and not str(x).startswith('open_') and not str(x).startswith('const_')]
    if not close_player_info:
        return
        
    random_char = random.choice(close_player_info)
    parts = random_char.split('_')
    char_group = parts[0]
    char_key = parts[1]
    char_val = parts[2] if len(parts) > 2 else ''
    
    await rq.update_characteristics(callback.from_user.id, char_key)
    
    msg = await retry_bad_decorate(bot.send_message)(
        text=f'<b>[{user_info[1]}] <a href="tg://user?id={user_info[3]}">{html.escape(user_info[2])}</a>:\n\n{char_group}: {char_val}</b>',
        parse_mode="HTML", chat_id=room.chat_id)
        
    room.round_msg.append(msg.message_id)
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>✅ Вы открыли характеристику:\n \n{char_group}: {char_val}\n \nПерейдите в чат для обсуждения</b>',
        reply_markup=await kb.link_chat(room.chat_id, msg.message_id), parse_mode="HTML")


@router.message(F.pinned_message, F.from_user.id == int(bot_id))
async def handle_pinned_msg(message: Message):
    try:
        await message.delete()
    except aiogram.exceptions.TelegramBadRequest:
        pass


@router.message(Command('StateClear'), F.from_user.id == admin_id, flags=flag_default)
async def cmd_state_clear(message: Message, bot: Bot, state: FSMContext):
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        target_id = int(args[1])
        state_user: FSMContext = await user_state(target_id, bot.id)
        await state_user.clear()
        await state.clear()
        await retry_after_decorate(message.answer)(text=f'Состояния игрока(id: {target_id}) очищены')