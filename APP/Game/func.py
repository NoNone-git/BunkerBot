import asyncio
import html
import random
import datetime
import re
from sqlalchemy import text

from aiogram.fsm.state import StatesGroup, State
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
import aiogram.exceptions

import APP.Game.keyboards as kb
from APP.Middlewares.decorators import retry_after_decorate, retry_bad_decorate
import APP.Game.requests as rq
from APP.Game.Classes import Room
from APP.BaseFunc.requests import select_prem_settings
from APP.BaseFunc.settings import PremiumSettings
from APP.Ads.requests import select_ad_end_post
from APP.Ads.set_ads import ad_preview
from APP.Game.requests import CHAR_INFO_RU
from APP.Game.ai_ending import ai_game_cache, get_ai_button


class PlayerState(StatesGroup):
    in_game = State()


chats_anti_flood_list = []


async def safe_delete_messages(bot: Bot, chat_id: int, message_ids: list):
    valid_ids = list(set([m for m in message_ids if m is not None and isinstance(m, int)]))
    if not valid_ids:
        return
        
    for i in range(0, len(valid_ids), 100):
        chunk = valid_ids[i:i + 100]
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
        except Exception:
            for msg_id in chunk:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass


round_next = ["ПЕРВЫЙ", "ВТОРОЙ", "ТРЕТИЙ", "ЧЕТВЕРТЫЙ", "ПЯТЫЙ", "ШЕСТОЙ", "СЕДЬMОЙ", "ВОСЬМОЙ"]
user_win_table = [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9]
round_table = [4, 4, 4, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7]

emoji_users = [
    '01', '02', '03', '04', '05', '06', '07', '08', '09',
    '10', '11', '12', '13', '14', '15', '16', '17', '18'
]


async def group_start(message: Message, bot: Bot, room: Room):
    await message.answer(text='Вы присоединились к игре')
    room_id = int(message.text.split()[1])
    await rq.update_room_id_group(message.from_user.id, room_id)
    room.players += 1
    await room.set_user(user_id=message.from_user.id, name=message.from_user.first_name)
    
    players_list = room.players_dict.values()
    result = ', '.join([f'<a href="tg://user?id={p["user_id"]}">{html.escape(p["name"])}</a>' for p in players_list])
    
    await retry_after_decorate(bot.edit_message_text)(
        text=f'<b>Ведется набор в игру\n\nПрисоединились:\n{result}\n\nВсего: {len(players_list)} чел.</b>',
        message_id=room.start_msg_id, chat_id=room_id,
        reply_markup=await kb.invite_bot_link(room_id),
        parse_mode="HTML")


async def start_game(room: Room, bot: Bot, message: Message):
    if room.settings.delete_messages:
        global chats_anti_flood_list
        chats_anti_flood_list.append(message.chat.id)
        
    room.win = user_win_table[room.players - 4]
    chat_status = await rq.get_chat_status(room.chat_id)
    
    if chat_status == 'premium':
        premium_settings = PremiumSettings(await select_prem_settings(message.chat.id))
        player_info = await rq.select_premium_char(message.chat.id, premium_settings, room.players)
        bunker_info = await rq.select_premium_bunker(message.chat.id, premium_settings)
    else:
        player_info = await rq.player_characteristics(room.players)
        bunker_info = await rq.bunker_characteristics()
        
    room.bunker['cataclysm'] = player_info['cataclysm']
    room.bunker['location'] = bunker_info['location'][0]
    room.bunker['supplies'] = bunker_info['supplies']
    room.bunker['rooms'] = bunker_info['rooms']
    
    txt = '<b>Участники игры:\n\n'
    players = list(room.players_dict.values())
    random.shuffle(players)
    
    cataclysm_title = player_info['cataclysm'].split('+')[0].capitalize()
    
    for index, player in enumerate(players):
        emoji = emoji_users[index]
        prof = player_info['profession'][index].capitalize()
        gend = player_info['gender'][index].capitalize()
        fact = player_info['fact'][index].capitalize()
        hobb = player_info['hobbies'][index].capitalize()
        bagg = player_info['baggage'][index].capitalize()
        heal = player_info['health'][index].capitalize()
        phob = player_info['phobia'][index].capitalize()
        addc = player_info['addiction'][index].capitalize()
        pers = player_info['persona'][index].capitalize()
        card = player_info['card'][index]
        
        await rq.insert_player_characteristics(
            player_id=player['user_id'], room_id=room.chat_id,
            profession=prof, gender=gend, fact=fact, cataclysm=cataclysm_title,
            hobbies=hobb, baggage=bagg, health=heal, phobia=phob,
            addiction=addc, persona=pers, card=card, emoji=emoji
        )
        
        room.players_dict[player['user_id']]['emoji'] = emoji
        card_desc = await rq.get_card(card)
        
        player_msg_text = (
            f'⚠️ Катастрофа: <b><i><u>{cataclysm_title}</u></i></b>\n\n'
            f'♦️ <b>Ваши характеристики:</b>\n\n'
            f'<blockquote>💼 Профессия: {prof}</blockquote>\n'
            f'<blockquote>👤 Био информация: {gend}</blockquote>\n'
            f'<blockquote>🫀 Здоровье: {heal}</blockquote>\n'
            f'<blockquote>🧩 Хобби: {hobb}</blockquote>\n'
            f'<blockquote>🎒 Багаж: {bagg}</blockquote>\n'
            f'<blockquote>✳ Доп. информация: {fact}</blockquote>\n'
            f'<blockquote>🕷 Фобия: {phob}</blockquote>\n'
            f'<blockquote>💊 Зависимость: {addc}</blockquote>\n'
            f'<blockquote>😎 Черта характера: {pers}</blockquote>\n\n'
            f'<blockquote>🃏 Карта действия №1: {card_desc}</blockquote>'
        )
        
        try:
            msg = (await retry_bad_decorate(bot.send_message)(
                chat_id=player['user_id'], text=player_msg_text,
                reply_markup=await kb.play_info(card=f'🃏 Карта действия_card_{card}'),
                parse_mode="HTML")).message_id
        except AttributeError:
            msg = 0
            
        txt += f'[{emoji}]  -  <a href="tg://user?id={player["user_id"]}">{html.escape(player["name"])}</a>\n'
        room.players_dict[player['user_id']]['msg_start'] = msg
        
    txt += '</b>'
    await retry_after_decorate(message.answer)(text=txt, reply_markup=kb.chat_game, parse_mode="HTML")
    
    loc = bunker_info['location'][0]
    sup1, sup2 = bunker_info['supplies'][0], bunker_info['supplies'][1]
    rm1, rm2, rm3 = bunker_info['rooms'][0], bunker_info['rooms'][1], bunker_info['rooms'][2]
    win_count = user_win_table[room.players - 4]
    
    msg_info: Message = await retry_after_decorate(message.answer)(
        text=f'🚨 <b>Катастрофа</b>: {cataclysm_title}\n\n'
             f'<b><i>Информация о бункере</i></b>:\n\n'
             f'🏕 <b>Бункер находится {loc}</b>\n\n'
             f'🧳 <b>В бункере есть</b>:\n{sup1}, {sup2}\n\n'
             f'⚠️ <b>Спец. комнаты</b>:\n{rm1}, {rm2}, {rm3}\n\n'
             f'👤 <b>Мест в бункере</b>: <i>{win_count}</i>',
        parse_mode='HTML')
        
    if room.settings.pin_info_game_msg:
        try:
            await retry_after_decorate(msg_info.pin)(disable_notification=True)
            room.start_msg_pin = msg_info.message_id
        except aiogram.exceptions.TelegramBadRequest:
            pass
            
    await asyncio.sleep(1)
    msg_id = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             f'<b><i>⏳ У вас есть {room.settings.time_start} сек. на изучение своих характеристик.</i></b>',
        parse_mode='HTML', reply_markup=kb.chat_game)).message_id
    room.round_msg.append(msg_id)
    
    await asyncio.sleep(room.settings.time_start)
    
    for player in players:
        info_player = await rq.get_player_by_id(player['user_id'])
        close_player_info = [x for x in info_player if x and not str(x).startswith('open_') and not str(x).startswith('const_')]
        
        if room.bot_open and room.bot_open != player['user_id']:
            try:
                msg_st = (await retry_bad_decorate(bot.send_message)(
                    chat_id=player['user_id'],
                    text='<b>🎲 Согласно карте действий, в этом раунде вы не можете выбирать, какую из характеристик открыть</b>',
                    reply_markup=kb.bot_open_characteristics, parse_mode="HTML")).message_id
            except AttributeError:
                msg_st = 0
        else:
            try:
                msg_st = (await retry_bad_decorate(bot.send_message)(
                    chat_id=player['user_id'],
                    text='<b>🧩 Выберите какую из характеристик хотите открыть</b>',
                    reply_markup=await kb.open_characteristics_group(close_player_info),
                    parse_mode="HTML")).message_id
            except AttributeError:
                msg_st = 0
        room.players_dict[player['user_id']]['msg_edit'] = msg_st
        
    msg_id2 = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             '<b><i>⏳ Пришло время открыть одну из характеристик.</i></b>',
        parse_mode='HTML', reply_markup=kb.chat_game)).message_id
    room.round_msg.append(msg_id2)
    
    half_time = int(room.settings.time_open / 2)
    await asyncio.sleep(half_time)
    
    if room.state != "stop_register" or room.round != 0:
        return
        
    msg_id3 = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             f'<b><i>⏳ Оставшееся время на открытие характеристики: {half_time} сек.</i></b>',
        parse_mode='HTML')).message_id
    room.round_msg.append(msg_id3)
    
    await asyncio.sleep(half_time)
    if room.state != "stop_register" or room.round != 0:
        return
        
    room.state = "start_discussion"
    await asyncio.sleep(2)
    
    if room.time_open or room.round != 0:
        return
        
    await room.set_votes_count()
    room_characteristics = await rq.select_open_characteristics_in_room(room.chat_id)
    
    if 0 in room_characteristics:
        not_open_characteristics = await rq.select_not_open_characteristics_in_room(room.chat_id)
        for user_id in not_open_characteristics:
            players_info = room.players_dict[user_id]
            info_player = await rq.get_player_by_id(user_id)
            close_player_info = [x for x in info_player if x and not str(x).startswith('open_') and not str(x).startswith('const_')]
            
            if close_player_info:
                random_characteristics = random.choice(close_player_info)
                parts = random_characteristics.split('_')
                char_group, char_key = parts[0], parts[1]
                char_val = parts[2] if len(parts) > 2 else ''
                
                room.players_dict[user_id]['open'] = 1
                await rq.update_characteristics(user_id, char_key)
                
                msg4 = (await retry_after_decorate(message.answer)(
                    text=f'<b>[{players_info["emoji"]}] <a href="tg://user?id={players_info["user_id"]}">{html.escape(players_info["name"])}</a>:\n\n'
                         f'{char_group}: {char_val}</b>',
                    parse_mode="HTML")).message_id
                room.round_msg.append(msg4)
                
                await retry_bad_decorate(bot.edit_message_text)(
                    chat_id=user_id, message_id=room.players_dict[user_id]['msg_edit'],
                    text=f'<b>✅ Вы открыли характеристику:\n\n{char_group}: {char_val}\n\nПерейдите в чат для обсуждения</b>',
                    reply_markup=await kb.link_chat(message.chat.id, msg4), parse_mode="HTML")
                    
    await votes_start(bot, message, room)


async def votes_start(bot: Bot, message: Message, room: Room):
    await asyncio.sleep(2)
    round_id = room.round
    users = await rq.get_active_players_emoji(room.chat_id)
    
    message_result = '💬 <b><i><u>НАЧАЛОСЬ ОБСУЖДЕНИЕ</u> 💬\n\n❇️ Характеристики игроков:</i>\n\n'
    for user in users:
        uid, uname = user[3], user[0]
        message_result += '<blockquote>'
        player_info = await rq.get_player_by_id(uid)
        open_player_info = [x for x in player_info if x and str(x).startswith('open_')]
        
        emoji = room.players_dict.get(uid, {}).get('emoji', '👤')
        message_result += f'[{emoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>:\n'
        for line in open_player_info:
            parts = line.split('_')
            if len(parts) >= 4:
                message_result += f'{parts[1]}: {parts[3]}\n'
        message_result += '</blockquote>'
        
    room.timer = room.settings.time_discussion
    msg_discussion = await retry_after_decorate(message.answer)(text=f'{message_result}</b>', parse_mode="HTML")
    
    if room.settings.pin_open_char:
        try:
            await retry_after_decorate(msg_discussion.pin)(disable_notification=True)
            room.pin_msg_ids.append(msg_discussion.message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
            
    room.round_msg.append(msg_discussion.message_id)
    
    if room.round % 2 == 1:
        await random_event(room, message, bot)
        
    if room.number_votes == 2:
        dis_text = '✌️ В этом раунде игру должны покинуть двое.'
    elif room.number_votes == 1:
        dis_text = '☝️ В этом раунде игру покидает 1 игрок.'
    else:
        dis_text = '👌 В этом раунде вы можете пропустить голосование или выгнать одного из участников.'
        
    admin_ext_text = '\n(Доступно только админам)' if room.settings.extend_discussion == 'Admins' else ''
    kb_markup = (await kb.stop_discussion(0, int(len(users) // 1.5), room.chat_id, room.settings.stop_discussion) 
                 if room.number_votes != 0 else 
                 await kb.next_round(0, int(len(users) // 2) + 1, room.chat_id, 0, room.settings.next_round, room.settings.stop_discussion))
                 
    skip_votes_msg = (await retry_after_decorate(message.answer)(
        parse_mode='HTML',
        text=f' <b><i>{dis_text}\n\n⌛️ Время на обсуждение: {int(room.settings.time_discussion)} сек.\nПродлить: /extend_discussion{admin_ext_text}</i></b>',
        reply_markup=kb_markup)).message_id
        
    room.round_msg.append(skip_votes_msg)
    room.skip_votes = skip_votes_msg
    
    if room.settings.time_discussion > 29:
        await asyncio.sleep(room.settings.time_discussion - 30)
        room.timer -= 30
    else:
        await asyncio.sleep(room.settings.time_discussion)
        room.timer = 0
        
    while room.timer > 0:
        if room.state != "start_discussion" or room.round != round_id:
            return False
        if room.timer % 30 != 0:
            await asyncio.sleep(room.timer - (room.timer // 30) * 30)
            room.timer -= room.timer - (room.timer // 30) * 30
            
        msg_id = (await retry_after_decorate(message.answer)(
            text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
                 f'<b><i>⏳ До завершения обсуждения {room.timer} сек.</i></b>',
            parse_mode='HTML')).message_id
        room.round_msg.append(msg_id)
        
        await asyncio.sleep(30)
        room.timer -= 30
        
    if room.state == "start_discussion" and room.round == round_id:
        room.state = "stop_discussion"
        await asyncio.sleep(2)
        if room.time_discussion == 0 and room.round == round_id:
            if room.number_votes == 1:
                await one_votes(room, bot, message)
            elif room.number_votes == 2:
                await two_votes(room, message, bot, 'первого', room.round)
            else:
                await one_votes(room, bot, message)


async def one_votes(room: Room, bot: Bot, message: Message):
    round_id = room.round
    users = await rq.get_active_players_emoji(room.chat_id)
    room.state = 'one_votes'
    
    try:
        await retry_bad_decorate(bot.delete_message)(chat_id=room.chat_id, message_id=room.skip_votes)
    except aiogram.exceptions.TelegramBadRequest:
        pass
        
    text = f'👉 <b><i><u>НАЧАЛО ГОЛОСОВАНИЯ</u> 👈\n\n<blockquote>'
    users.sort()
    for user in users:
        v_emoji = user[2]
        v_count = user[4]
        
        if not room.settings.anonymous_votes:
            vote_display = '0' if v_emoji is None else str(v_emoji)
        else:
            vote_display = '0' if v_emoji is None else str(v_count)
            
        text += f'[{user[1]}] <a href="tg://user?id={user[3]}">{html.escape(user[0])}</a>: {vote_display}\n'
    text += '</blockquote></i></b>'
    
    if room.number_votes == 0:
        skip = await rq.get_skip_votes_players(room.chat_id)
        skip_val = skip[0] if not room.settings.anonymous_votes else skip[1]
        text += f'\n<b><i>❎  Скип: {skip_val}\n\n🤫 В этом раунде голосование можно пропустить</i></b>'
        
    msg = await retry_after_decorate(message.answer)(text=text, reply_markup=kb.bot_link_votes, parse_mode="HTML")
    
    if room.settings.pin_votes_msg:
        try:
            await retry_after_decorate(msg.pin)(disable_notification=True)
            room.pin_msg_ids.append(msg.message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
            
    room.round_msg.append(msg.message_id)
    room.votes_msg_id = msg.message_id
    
    players = [user for user in room.players_dict.values() if user['active'] == 1]
    
    for player in players:
        await retry_bad_decorate(bot.edit_message_text)(
            chat_id=player['user_id'], message_id=player['msg_edit'],
            text='🫵 Выберите игрока, которого хотите выгнать.',
            reply_markup=await kb.group_player_voice(room.chat_id, player['user_id'], room.number_votes))
            
    half_time = int(room.settings.time_votes / 2)
    await asyncio.sleep(half_time)
    
    if room.state != 'one_votes' or room.round != round_id:
        return False
        
    msg_id = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             f'<b><i>⏳ До конца голосования {half_time} сек.</i></b>',
        parse_mode='HTML')).message_id
    room.round_msg.append(msg_id)
    
    await asyncio.sleep(half_time)
    
    if room.state == 'one_votes' and room.round == round_id:
        room.state = "stop_votes"
        await asyncio.sleep(2)
        if room.time_votes == 0 and room.round == round_id:
            await finish_one_votes(message, bot, room)
        else:
            return False
    else:
        return False


async def finish_one_votes(message: Message, bot: Bot, room: Room):
    voting_results_message = await finish_votes(room, message, bot)
    players = [user for user in room.players_dict.values() if user['active'] == 1]
    
    if len(players) > user_win_table[room.players - 4]:
        for player in players:
            try:
                await retry_bad_decorate(bot.edit_message_text)(
                    chat_id=player['user_id'], message_id=player['msg_edit'],
                    text=f'<b>☑️ Голосование завершено. Итоги голосования подведены в чате.\nДо начала нового раунда {room.settings.time_round} сек.</b>',
                    reply_markup=await kb.link_chat(message.chat.id, voting_results_message),
                    parse_mode='HTML')
            except aiogram.exceptions.TelegramBadRequest:
                pass
                
        await asyncio.sleep(room.settings.time_round)
        await new_round(room, bot, message)
        
    elif len(players) <= user_win_table[room.players - 4]:
        msg_finish = await finish_game(players, message, room, bot)
        for player in players:
            await retry_bad_decorate(bot.edit_message_text)(
                chat_id=player['user_id'], message_id=player['msg_edit'],
                text='<b>☑️ Голосование завершено. Итоги голосования подведены в чате</b>',
                parse_mode='HTML')
            await retry_bad_decorate(bot.send_message)(
                chat_id=player['user_id'],
                text='<b>🏆 Поздравляю с победой!!! Вам начислено 30 монет 🪙</b>',
                parse_mode='HTML', reply_markup=await kb.link_chat(message.chat.id, msg_finish))


async def finish_votes(room: Room, message: Message, bot: Bot):
    player_info = await rq.get_voice_for_player_info(room.chat_id) 
    voice_for_player = [p[0] or 0 for p in player_info]
    max_v = max(voice_for_player) if voice_for_player else 0
    
    player_out = await rq.get_player_out(room.chat_id, max_v)
    
    if not player_out:
        active_users = [p for p in room.players_dict.values() if p.get('active') == 1]
        if not active_users:
            return room.votes_msg_id 
        fallback = random.choice(active_users)
        player_out = [(fallback['user_id'], fallback['name'], fallback.get('emoji', '👤'))]

    if room.number_votes == 0:
        votes_skip_info = await rq.get_skip_votes(room.chat_id)
        if votes_skip_info > max_v:
            msg = (await retry_after_decorate(message.answer)(
                text=f'<b><i>❗️ В этом раунде было принято решение никого не выгонять.\nДо начала нового раунда {room.settings.time_round} сек.</i></b>',
                parse_mode='HTML')).message_id
            room.round_msg.append(msg)
            return msg
        elif len(player_out) > 1:
            msg = (await retry_after_decorate(message.answer)(
                text=f'<b><i>❗️ Так как мнение игроков разошлось, в этом раунде никого не выгоняем\nДо начала нового раунда {room.settings.time_round} сек.</i></b>',
                parse_mode='HTML')).message_id
            room.round_msg.append(msg)
            return msg
            
    user_out = random.choice(player_out) if len(player_out) > 1 else player_out[0]
    
    users = await rq.get_active_players_emoji(room.chat_id)
    users.sort()
    
    text = f'👉 <b><i><u>НАЧАЛО ГОЛОСОВАНИЯ</u> 👈\n\n<blockquote expandable>'
    for user in users:
        uid, uname, uemoji, v_emoji, v_count = user[3], user[0], user[1], user[2], user[4]
        
        if not room.settings.anonymous_votes:
            vote_display = '0' if v_emoji is None else str(v_emoji)
        else:
            vote_display = '0' if v_emoji is None else str(v_count)
            
        is_target = '🫵' if uid == user_out[0] else ''
        text += f'[{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>: {vote_display} {is_target}\n'
        
    text += '</blockquote></i></b>'
    
    if room.number_votes == 0:
        skip = await rq.get_skip_votes_players(room.chat_id)
        skip_val = skip[0] if not room.settings.anonymous_votes else skip[1]
        text += f'\n<b><i>❎  Скип: {skip_val}\n\n🤫 В этом раунде голосование можно пропустить</i></b>'
        
    await retry_bad_decorate(bot.edit_message_text)(
        chat_id=room.chat_id, message_id=room.votes_msg_id,
        text=text, reply_markup=kb.bot_link_votes, parse_mode="HTML")
        
    card_raw = await rq.get_user_card(user_out[0])
    await room.out(user_out[0], bot)
    
    if card_raw and 'card5' in str(card_raw):
        await auto_use_card(user_out, str(card_raw), room, bot, message)
        
    player_info_db = await rq.get_player_by_id(user_out[0])
    active_info = [x for x in player_info_db if x and not str(x).startswith('const_')]
    
    info_text = ''
    for info in active_info:
        parts = info.split('_')
        if len(parts) >= 3:
            info_text += f'{parts[-3]}: {parts[-1]}\n\n'
            
    await retry_after_decorate(message.answer)(
        text=f' <b><i><u>🫵 Вы выгнали игрока</u> <a href="tg://user?id={user_out[0]}">{html.escape(user_out[1])}</a>!\n\n'
             f'🎭 Его характеристики:</i></b>\n\n<blockquote expandable>{info_text}</blockquote>\n'
             f'⏳ <b><i>До начала нового раунда {room.settings.time_round} сек.</i></b>',
        parse_mode="HTML")
        
    await retry_bad_decorate(bot.edit_message_text)(
        text='<b>Вы проиграли. Вам начислено 10 монет 🪙</b>',
        chat_id=user_out[0], message_id=room.players_dict[user_out[0]]['msg_edit'], parse_mode="HTML")
        
    if not hasattr(room, 'player_out'):
        room.player_out = []
    room.player_out.append(room.players_dict.get(user_out[0], {'user_id': user_out[0], 'name': user_out[1]}))
    
    return room.votes_msg_id


async def result_two_votes(room: Room, bot: Bot, message: Message):
    if len(room.player_out) < 2:
        pass 
    else:
        p1, p2 = room.player_out[0], room.player_out[1]
        await retry_after_decorate(message.answer)(
            text=f'<b>В этом раунде игру покинули:\n'
                 f' - [{p1.get("emoji", "👤")}] <a href="tg://user?id={p1["user_id"]}">{html.escape(p1["name"])}</a>\n'
                 f' - [{p2.get("emoji", "👤")}] <a href="tg://user?id={p2["user_id"]}">{html.escape(p2["name"])}</a>\n'
                 f'⏳ До начала нового раунда {room.settings.time_round} сек.</b>',
            parse_mode='HTML')
            
    for user in room.player_out:
        full_player_info = await rq.get_player_by_id(user['user_id'])
        player_info = [x for x in full_player_info if x and not str(x).startswith('const_')]
        
        info_text = ''
        for info in player_info:
            parts = info.split('_')
            if len(parts) >= 3:
                info_text += f'{parts[-3]}: {parts[-1]}\n\n'
                
        await retry_after_decorate(message.answer)(
            text=f' <b><i><u>🫵 Вы выгнали игрока</u> <a href="tg://user?id={user["user_id"]}">{html.escape(user["name"])}</a>!\n\n'
                 f'🎭 Его характеристики:</i></b>\n\n<blockquote expandable>{info_text}</blockquote>',
            parse_mode="HTML")
        await asyncio.sleep(1)
        
    players = [user for user in room.players_dict.values() if user['active'] == 1]
    
    if len(players) > user_win_table[room.players - 4]:
        for user in players:
            await retry_bad_decorate(bot.edit_message_text)(
                chat_id=user['user_id'], message_id=user['msg_edit'],
                text=f'<b>☑️ Голосование завершено. Итоги голосования подведены в чате.\nДо начала нового раунда {room.settings.time_round} сек.<b>',
                reply_markup=await kb.link_chat(message.chat.id, room.votes_msg_id), parse_mode="HTML")
        await asyncio.sleep(room.settings.time_round)
        await new_round(room, bot, message)
    elif len(players) <= user_win_table[room.players - 4]:
        await asyncio.sleep(2)
        msg_finish = await finish_game(players, message, room, bot)
        for user in players:
            await retry_bad_decorate(bot.edit_message_text)(
                chat_id=user['user_id'], message_id=user['msg_edit'],
                text='<b>☑️ Голосование завершено. Итоги голосования подведены в чате.</b>', parse_mode="HTML")
            await retry_bad_decorate(bot.send_message)(
                chat_id=user['user_id'], text='<b>🏆 Поздравляю с победой!!! Вам начислено 30 монет 🪙</b>',
                parse_mode="HTML", reply_markup=await kb.link_chat(message.chat.id, msg_finish))


async def two_votes(room: Room, message: Message, bot: Bot, msg_text, round_info):
    state_text = "first_two_votes" if msg_text == 'первого' else "second_two_votes"
    room.state = state_text
    users = await rq.get_active_players_emoji(room.chat_id)
    
    try:
        await retry_bad_decorate(bot.delete_message)(chat_id=room.chat_id, message_id=room.skip_votes)
    except aiogram.exceptions.TelegramBadRequest:
        pass
        
    text = f'👉 <b><i><u>НАЧАЛО ГОЛОСОВАНИЯ</u> 👈\n\n<blockquote>'
    users.sort()
    for user in users:
        uid, uname, uemoji, v_emoji, v_count = user[3], user[0], user[1], user[2], user[4]
        if not room.settings.anonymous_votes:
            vote_display = '0' if v_emoji is None else str(v_emoji)
        else:
            vote_display = '0' if v_emoji is None else str(v_count)
            
        text += f'[{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>: {vote_display}\n'
    text += '</blockquote></i></b>'
    
    msg = await retry_after_decorate(message.answer)(text=text, reply_markup=kb.bot_link_votes, parse_mode="HTML")
    
    if room.settings.pin_votes_msg:
        try:
            await retry_after_decorate(msg.pin)(disable_notification=True)
            room.pin_msg_ids.append(msg.message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
            
    room.round_msg.append(msg.message_id)
    room.votes_msg_id = msg.message_id
    
    players = [user for user in room.players_dict.values() if user['active'] == 1]
    for player in players:
        await retry_bad_decorate(bot.edit_message_text)(
            chat_id=player['user_id'], message_id=player['msg_edit'],
            parse_mode='HTML', text='<b>🫵 Выберите игрока, которого хотите выгнать</b>',
            reply_markup=await kb.group_player_voice(room.chat_id, player['user_id'], 1))
            
    half_time = int(room.settings.time_votes / 2)
    await asyncio.sleep(half_time)
    
    if room.state != state_text or room.round != round_info:
        return False
        
    msg_id = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             f'<b><i>⏳ До конца голосования {half_time} сек.</i></b>',
        parse_mode='HTML')).message_id
    room.round_msg.append(msg_id)
    
    await asyncio.sleep(half_time)
    
    if room.state == state_text and room.round == round_info:
        room.state = "stop_votes"
        await asyncio.sleep(2)
        res = room.time_votes if msg_text == 'первого' else room.time_two_votes
        if res:
            return
        await finish_two_votes(room, message, bot, msg_text)
    else:
        return False


async def finish_two_votes(room: Room, message: Message, bot: Bot, msg_text):
    player_info = await rq.get_voice_for_player_info(room.chat_id)
    voice_for_player = [p[0] or 0 for p in player_info]
    max_v = max(voice_for_player) if voice_for_player else 0
    
    player_out = await rq.get_player_out(room.chat_id, max_v)
    
    if not player_out:
        active_users = [p for p in room.players_dict.values() if p.get('active') == 1]
        if not active_users:
            return
        fallback = random.choice(active_users)
        player_out = [(fallback['user_id'], fallback['name'], fallback.get('emoji', '👤'))]

    user_out = random.choice(player_out) if len(player_out) > 1 else player_out[0]
    
    users = await rq.get_active_players_emoji(room.chat_id)
    users.sort()
    
    text = f'👉 <b><i><u>НАЧАЛО ГОЛОСОВАНИЯ</u> 👈\n\n<blockquote expandable>'
    for user in users:
        uid, uname, uemoji, v_emoji, v_count = user[3], user[0], user[1], user[2], user[4]
        
        if not room.settings.anonymous_votes:
            vote_display = '0' if v_emoji is None else str(v_emoji)
        else:
            vote_display = '0' if v_emoji is None else str(v_count)
            
        is_target = '🫵' if uid == user_out[0] else ''
        text += f'[{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>: {vote_display} {is_target}\n'
        
    text += '</blockquote></i></b>'
    
    await retry_bad_decorate(bot.edit_message_text)(
        chat_id=message.chat.id, message_id=room.votes_msg_id, text=text,
        reply_markup=kb.bot_link_votes, parse_mode="HTML")
        
    card_raw = await rq.get_user_card(user_out[0])
    await room.out(user_out[0], bot)
    
    if card_raw and 'card5' in str(card_raw):
        await auto_use_card(user_out, str(card_raw), room, bot, message)
        
    await retry_bad_decorate(bot.edit_message_text)(
        text='<b>Вы проиграли. Вам начислено 10 монет 🪙</b>',
        chat_id=user_out[0], message_id=room.players_dict[user_out[0]]['msg_edit'])
        
    if not hasattr(room, 'player_out'):
        room.player_out = []
    room.player_out.append(room.players_dict.get(user_out[0], {'user_id': user_out[0], 'name': user_out[1]}))
    
    if msg_text == 'первого':
        await room.new_votes()
        await two_votes(room, message, bot, 'второго', room.round)
    else:
        await result_two_votes(room, bot, message)


async def _delayed_delete_ai_offer(bot: Bot, chat_id: int, message_id: int):
    await asyncio.sleep(180)
    if chat_id in ai_game_cache:
        ai_game_cache.pop(chat_id, None)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass


async def new_round(room: Room, bot: Bot, message: Message):
    players = []
    text_lines = []
    number_of_players = 0
    
    for user in room.players_dict.values():
        if user['active'] == 1:
            number_of_players += 1
            players.append(user)
            text_lines.append(f'{number_of_players}. <a href="tg://user?id={user["user_id"]}">{html.escape(user["name"])}</a>')
            
    text = '\n'.join(text_lines)
    
    if room.settings.delete_round_msgs and room.round_msg:
        await safe_delete_messages(bot, room.chat_id, room.round_msg)
        
    if room.pin_msg_ids:
        for msg in room.pin_msg_ids:
            try:
                await retry_bad_decorate(bot.unpin_chat_message)(chat_id=room.chat_id, message_id=msg)
            except aiogram.exceptions.TelegramBadRequest:
                pass
                
    await rq.new_round(room.chat_id)
    await room.new_round_update()
    
    round_name = round_next[room.round] if room.round < len(round_next) else str(room.round + 1)
    
    msg_id = (await retry_after_decorate(message.answer)(
        text=f'☑️ <b><i><u>{round_name} РАУНД</u></i></b> ☑️\n\nАктивные игроки:\n<blockquote expandable>{text}</blockquote>\n👤 <b><i><u>Всего</u>:</i></b> {number_of_players}',
        reply_markup=kb.chat_game, parse_mode='HTML')).message_id
    room.round_msg.append(msg_id)
    
    await bot_send_start_message(bot, message, players, room)


async def bot_send_start_message(bot: Bot, message: Message, players, room: Room):
    room.state = 'start_open'
    round_info0 = room.round
    
    for player in players:
        player_info = await rq.get_player_by_id(player['user_id'])
        close_player_info = [x for x in player_info if x and not str(x).startswith('open_') and not str(x).startswith('const_')]
        
        if room.bot_open and room.bot_open != player['user_id']:
            await retry_bad_decorate(bot.edit_message_text)(
                chat_id=player['user_id'], message_id=player['msg_edit'],
                text='<b>🎲 Согласно карте действий, в этом раунде вы не можете выбирать, какую из характеристик открыть</b>',
                reply_markup=kb.bot_open_characteristics, parse_mode='HTML')
        else:
            await retry_bad_decorate(bot.edit_message_text)(
                chat_id=player['user_id'], message_id=player['msg_edit'],
                text='<b>🧩 Выберите какую из характеристик хотите открыть</b>',
                reply_markup=await kb.open_characteristics_group(close_player_info), parse_mode='HTML')
                
    half_time = int(room.settings.time_open / 2)
    await asyncio.sleep(half_time)
    
    if room.state != "start_open" or room.round != round_info0:
        return False
        
    msg_id = (await retry_after_decorate(message.answer)(
        text='<blockquote>❗️————<b><i><u>УВЕДОМЛЕНИЕ</u></i></b>————❗️</blockquote>'
             f'<b><i>⏳ Оставшееся время на открытие характеристики: {half_time} сек.</i></b>',
        parse_mode='HTML')).message_id
    room.round_msg.append(msg_id)
    
    await asyncio.sleep(half_time)
    if room.state != "start_open" or room.round != round_info0:
        return False
        
    room.state = "start_discussion"
    await asyncio.sleep(2)
    
    if room.time_open or room.round != round_info0:
        return
        
    await room.set_votes_count()
    room_characteristics = await rq.select_open_characteristics_in_room(room.chat_id)
    
    if 0 in room_characteristics:
        not_open_characteristics = await rq.select_not_open_characteristics_in_room(room.chat_id)
        for user_id in not_open_characteristics:
            players_info = await rq.get_user_info(user_id)
            info_player = await rq.get_player_by_id(user_id)
            close_player_info = [x for x in info_player if x and not str(x).startswith('open_') and not str(x).startswith('const_')]
            
            if close_player_info:
                random_characteristics = random.choice(close_player_info)
                parts = random_characteristics.split('_')
                char_group, char_key = parts[0], parts[1]
                char_val = parts[2] if len(parts) > 2 else ''
                
                await rq.update_characteristics(user_id, char_key)
                
                msg = (await retry_after_decorate(message.answer)(
                    text=f'[{players_info[1]}] <a href="tg://user?id={players_info[3]}">{html.escape(players_info[2])}</a>:\n\n{char_group}: {char_val}',
                    parse_mode="HTML")).message_id
                room.round_msg.append(msg)
                room.players_dict[user_id]['open'] = 1
                
                await retry_bad_decorate(bot.edit_message_text)(
                    chat_id=user_id, message_id=room.players_dict[user_id]['msg_edit'],
                    text=f'<b>✅ Вы открыли характеристику:\n\n{char_group}: {char_val}\n\nПерейдите в чат для обсуждения</b>',
                    reply_markup=await kb.link_chat(message.chat.id, msg), parse_mode="HTML")
                    
    await votes_start(bot, message, room)


async def finish_game(active_user, message: Message, room: Room, bot: Bot):
    text1_list = []
    for user in active_user:
        await rq.player_win(user['user_id'])
        text1_list.append(f'<a href="tg://user?id={user["user_id"]}">{html.escape(user["name"])}</a>')
        
    text1 = ', '.join(text1_list)
    
    if room.settings.delete_round_msgs and room.round_msg:
        await safe_delete_messages(bot, room.chat_id, room.round_msg)
        
    msg = (await retry_after_decorate(message.answer)(
        text=f'-------------ИГРА ЗАВЕРШЕНА-------------\n\n'
             f'<b>👑 ПОБЕДИТЕЛИ:\n{text1}\n\n'
             f'✅ А сейчас пришло время узнать всю информацию о победителях и понять правильный ли вы сделали выбор!</b>',
        parse_mode="HTML")).message_id
        
    try:
        if message.chat.id in chats_anti_flood_list:
            chats_anti_flood_list.remove(message.chat.id)
    except ValueError:
        pass
        
    text_blocks = []
    player_links = []
    
    for user in room.players_dict.values():
        await safe_delete_messages(bot, user['user_id'], [user.get('msg_edit'), user.get('msg_start')])
        
    for player in active_user:
        player_info_db = await rq.get_player_by_id(player['user_id'])
        player_info = [x for x in player_info_db if x and not str(x).startswith('const_')]
        
        player_links.append(f'<a href="tg://user?id={player["user_id"]}">{html.escape(player["name"])}</a>')
        
        p_block = f'<a href="tg://user?id={player["user_id"]}">{html.escape(player["name"])}</a>:\n<blockquote expandable>'
        for info in player_info:
            parts = info.split('_')
            if len(parts) >= 3:
                p_block += f'{parts[-3]}: {parts[-1]}\n\n'
        p_block += '</blockquote>'
        text_blocks.append(p_block)
        
    player_text = ', '.join(player_links)
    final_text = '\n'.join(text_blocks)
    
    await retry_after_decorate(message.answer)(
        text=f'<b><i>👑 Игроки {player_text} прошли в бункер!\n\n🎭 Их характеристики:\n{final_text}</i></b>',
        parse_mode="HTML")
        
    await asyncio.sleep(2)
    chat_status = await rq.get_chat_status(room.chat_id)
    
    if chat_status != 'premium':
        data = await select_ad_end_post(ad_date=str(datetime.date.today()))
        await ad_preview(data, message.chat.id, bot)
    else:
        survivors_text = ""
        for player in active_user:
            player_info_db = await rq.get_player_by_id(player['user_id'])
            active_info = [x for x in player_info_db if x and not str(x).startswith('const_')]
            info_str = ", ".join([f"{i.split('_')[-3]}: {i.split('_')[-1]}" for i in active_info if len(i.split('_')) >= 3])
            survivors_text += f"- {player['name']} ({info_str})\n"
            
        kicked_text = ""
        if hasattr(room, 'player_out') and room.player_out:
            for p in room.player_out:
                p_db = await rq.get_player_by_id(p['user_id'])
                act_info = [x for x in p_db if x and not str(x).startswith('const_')]
                inf = ", ".join([f"{i.split('_')[-3]}: {i.split('_')[-1]}" for i in act_info if len(i.split('_')) >= 3])
                kicked_text += f"- {p['name']} ({inf})\n"
        else:
            kicked_text = "Никто не был изгнан"
        
        bunker_details = (f"Расположение: {room.bunker.get('location', 'Неизвестно')}\n"
                          f"Запасы: {', '.join(room.bunker.get('supplies', []))}\n"
                          f"Комнаты: {', '.join(room.bunker.get('rooms', []))}")
                          
        ai_game_cache[room.chat_id] = {
            'survivors': survivors_text,
            'kicked': kicked_text,
            'cataclysm': room.bunker.get('cataclysm', ''),
            'bunker': bunker_details,
            'events': "\n".join(room.events_text) if room.events_text else "Без происшествий",
            'ai_format': getattr(room.prem_settings, 'ai_format', 0) if hasattr(room, 'prem_settings') else 0
        }
        
        ai_msg = await retry_after_decorate(message.answer)(
            text="<b>🧠 Хотите узнать, как сложилась судьба выживших в бункере?</b>\n<i>Нейросеть сгенерирует финал на основе ваших характеристик (Доступно 3 минуты).</i>",
            reply_markup=get_ai_button(room.chat_id),
            parse_mode="HTML"
        )
        asyncio.create_task(_delayed_delete_ai_offer(bot, room.chat_id, ai_msg.message_id))

    await rq.chat_game(message.chat.id, message.chat.full_name, (await bot.get_chat_member_count(message.chat.id)))
    await room.close_room(bot=bot)
    return msg


async def random_event(room: Room, message: Message, bot: Bot):
    chat_status = await rq.get_chat_status(room.chat_id)
    custom_events = []
    
    # 1. Загружаем кастомные события, если чат премиум
    if chat_status == 'premium':
        async with rq.engine.connect() as conn:
            # Страховочное создание таблиц (на случай если не создались)
            await conn.execute(text("CREATE TABLE IF NOT EXISTS premium_events_status (chat_id BIGINT PRIMARY KEY, is_active INTEGER DEFAULT 0)"))
            await conn.execute(text("CREATE TABLE IF NOT EXISTS premium_events (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id BIGINT, event_type INTEGER, event_text TEXT)"))
            
            is_active = await conn.scalar(text("SELECT is_active FROM premium_events_status WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            if is_active:
                res = await conn.execute(text("SELECT id, event_type, event_text FROM premium_events WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
                custom_events = res.fetchall()
                
    # 2. ИСПОЛЬЗУЕМ 100% ПРЕМИУМ СОБЫТИЯ, пока они не кончатся в текущей игре
    if custom_events:
        available_custom = [e for e in custom_events if f"custom_{e[0]}" not in room.events_ids]
        if available_custom:
            c_ev = random.choice(available_custom)
            ev_id = f"custom_{c_ev[0]}"
            ev_type = c_ev[1]
            ev_text = c_ev[2]
            
            # Подставляем игроков, игнорируя регистр (re.IGNORECASE)
            active_users = [user for user in room.players_dict.values() if user['active'] == 1]
            if ev_type == 1 and active_users:
                p = random.choice(active_users)
                player_str = f'[{p.get("emoji", "👤")}] <a href="tg://user?id={p["user_id"]}">{html.escape(p["name"])}</a>'
                ev_text = re.sub(r'\[игрок\]', player_str, ev_text, flags=re.IGNORECASE)
                
            elif ev_type == 2 and len(active_users) >= 2:
                p1, p2 = random.sample(active_users, 2)
                player1_str = f'[{p1.get("emoji", "👤")}] <a href="tg://user?id={p1["user_id"]}">{html.escape(p1["name"])}</a>'
                player2_str = f'[{p2.get("emoji", "👤")}] <a href="tg://user?id={p2["user_id"]}">{html.escape(p2["name"])}</a>'
                ev_text = re.sub(r'\[игрок1\]', player1_str, ev_text, flags=re.IGNORECASE)
                ev_text = re.sub(r'\[игрок2\]', player2_str, ev_text, flags=re.IGNORECASE)
                
            msg_id = (await retry_after_decorate(message.answer)(
                text=f'<blockquote>🔈 <b><i><u>СЛУЧАЙНОЕ СОБЫТИЕ</u></i></b>  🔈</blockquote>\n\n<b><i>{ev_text}</i></b>', 
                parse_mode="HTML")).message_id
            room.round_msg.append(msg_id)
            room.events_ids.append(ev_id)
            room.events_text.append(re.sub(r'<[^>]+>', '', ev_text))
            return

    # 3. Стандартные события (Используются, если премиум нет, они выключены или уже кончились)
    event = await rq.select_random_event(room.events_ids)
    if not event:
        return
        
    ev_name = event[0]
    ev_id = event[1]
    ev_code = event[2]
    
    if ev_code == 'event1':
        await rq.delete_baggage(room.chat_id)
        active_user = [user['user_id'] for user in room.players_dict.values() if user['active'] == 1]
        await update_info(bot, active_user, room)
        msg_id = (await retry_after_decorate(message.answer)(
            text=f'<blockquote>🔈 <b><i><u>СЛУЧАЙНОЕ СОБЫТИЕ</u></i></b>  🔈</blockquote>\n\n<b><i>{ev_name}</i></b>', 
            parse_mode="HTML")).message_id
        room.round_msg.append(msg_id)
    elif ev_code == 'event2':
        active_users = [user for user in room.players_dict.values() if user['active'] == 1]
        if active_users:
            player = random.choice(active_users)
            ev_parts = ev_name.split('_')
            p1 = ev_parts[0] if len(ev_parts) > 0 else ''
            p2 = ev_parts[1] if len(ev_parts) > 1 else ''
            event_text = f'{p1} <a href="tg://user?id={player["user_id"]}">{html.escape(player["name"])}</a> {p2}'
            msg_id = (await retry_after_decorate(message.answer)(
                text=f'<blockquote>🔈 <b><i><u>СЛУЧАЙНОЕ СОБЫТИЕ</u></i></b>  🔈</blockquote>\n\n<b><i>{event_text}</i></b>', 
                parse_mode="HTML")).message_id
            room.round_msg.append(msg_id)
    elif ev_code == 'event3':
        active_users = [user for user in room.players_dict.values() if user['active'] == 1]
        if len(active_users) >= 2:
            players = random.choices(active_users, k=2)
            ev_parts = ev_name.split('_')
            p1 = ev_parts[0] if len(ev_parts) > 0 else ''
            p2 = ev_parts[1] if len(ev_parts) > 1 else ''
            p3 = ev_parts[2] if len(ev_parts) > 2 else ''
            event_text = f'{p1}<a href="tg://user?id={players[0]["user_id"]}">{html.escape(players[0]["name"])}</a>{p2}<a href="tg://user?id={players[1]["user_id"]}">{html.escape(players[1]["name"])}</a>{p3}'
            msg_id = (await retry_after_decorate(message.answer)(
                text=f'<blockquote>🔈 <b><i><u>СЛУЧАЙНОЕ СОБЫТИЕ</u></i></b>  🔈</blockquote>\n\n<b><i>{event_text}</i></b>', 
                parse_mode="HTML")).message_id
            room.round_msg.append(msg_id)
    else:
        msg_id = (await retry_after_decorate(message.answer)(
            text=f'<blockquote>🔈 <b><i><u>СЛУЧАЙНОЕ СОБЫТИЕ</u></i></b>  🔈</blockquote>\n\n<b><i>{ev_name}</i></b>', 
            parse_mode="HTML")).message_id
        room.round_msg.append(msg_id)
        
    room.events_ids.append(ev_id)
    clean_ev_name = ev_name.replace('_', ' ')
    room.events_text.append(clean_ev_name)


async def card_2(callback: CallbackQuery):
    parts = callback.data.split('_')
    target_id = parts[2]
    char_type = parts[3]
    
    char_raw = await rq.select_char_player_card(char_type, target_id)
    char_val = char_raw.split('_')[-1] if char_raw else 'Неизвестно'
    result = CHAR_INFO_RU.get(char_type, '🫀 Здоровье')
    name = await rq.get_name(target_id)
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>Вы подсмотрели характеристику игрока {html.escape(name)}:\n{result}: {char_val}</b>',
        reply_markup=kb.back_game_info, parse_mode='HTML')


async def card_1(callback: CallbackQuery, bot: Bot, room: Room):
    parts = callback.data.split('_')
    target_id = parts[2]
    char_type = parts[3]
    
    result = CHAR_INFO_RU.get(char_type, '🫀 Здоровье')
    result_char = await rq.change_characteristics(char_type, callback.from_user.id, target_id, result)
    
    name_info = await rq.get_user_info(target_id)
    user_info = await rq.get_user_info(callback.from_user.id)
    
    val1 = result_char[0].split('_')[-1] if result_char[0] else '?'
    val2 = result_char[1].split('_')[-1] if result_char[1] else '?'
    
    await retry_bad_decorate(callback.message.edit_text)(
        text=f'<b>Вы поменялись характеристикой {result} с игроком {html.escape(name_info[2])}\n'
             f'новые значения характеристики:\n\n'
             f'<a href="tg://user?id={user_info[3]}">{html.escape(user_info[2])}</a>: {val1}\n'
             f'<a href="tg://user?id={name_info[3]}">{html.escape(name_info[2])}</a>: {val2}</b>',
        parse_mode="HTML", reply_markup=kb.back_game_info)
        
    await update_info(bot, [target_id], room)
    
    msg_id = (await retry_after_decorate(bot.send_message)(
        chat_id=room.chat_id,
        text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
             f'<b><i>Игрок [{user_info[1]}] <a href="tg://user?id={user_info[3]}">{html.escape(user_info[2])}</a> '
             f'поменялся картой \n{result} с игроком [{name_info[1]}] <a href="tg://user?id={name_info[3]}">{html.escape(name_info[2])}</a></i></b>',
        parse_mode="HTML")).message_id
    room.round_msg.append(msg_id)


async def card_4(callback: CallbackQuery, bot: Bot, room: Room):
    parts = callback.data.split('_')
    target_id = parts[2]
    char_type = parts[3]
    
    name = await rq.get_user_info(target_id)
    
    if char_type == 'phobia':
        result = '🕷 Фобия'
        msg_result = 'фобию'
        result_char = 'Отсутствует'
    elif char_type == 'health':
        msg_result = 'болезнь'
        result = '🫀 Здоровье'
        result_char = 'Здоров'
    else:
        msg_result = 'зависимость'
        result = '💊 Зависимость'
        result_char = 'Отсутствует'
        
    await rq.healer_characteristics(char_type, target_id, result_char, result)
    
    if int(target_id) == callback.from_user.id:
        await retry_bad_decorate(callback.message.edit_text)(
            text=f'<b>Вы вылечили {msg_result} у себя. Новое значение:\n<i>{result}: {result_char}</i></b>', 
            parse_mode='HTML', reply_markup=kb.back_game_info)
    else:
        await retry_bad_decorate(callback.message.edit_text)(
            text=f'<b>Вы вылечили {msg_result} у игрока [{name[1]}] <a href="tg://user?id={name[3]}">{html.escape(name[2])}</a>. '
                 f'Новое значение:\n<i>{result}: {result_char}</i></b>', 
            parse_mode='HTML', reply_markup=kb.back_game_info)
            
    msg_id = (await retry_after_decorate(bot.send_message)(
        chat_id=room.chat_id,
        text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
             f'<b><i>Значение характеристики {result} игрока '
             f'[{name[1]}] <a href="tg://user?id={name[3]}">{html.escape(name[2])}</a> '
             f'заменено на {result_char}</i></b>',
        parse_mode="HTML")).message_id
    room.round_msg.append(msg_id)


async def auto_use_card(user, card: str, room: Room, bot: Bot, message: Message):
    users = await rq.get_active_user_in_room(room.chat_id)
    players = [x[0] for x in users]
    
    card_parts = card.split('_')
    card_action = card_parts[3] if len(card_parts) > 3 else ''
    
    if isinstance(user, dict):
        uid = user.get('user_id')
        uname = user.get('name')
        uemoji = user.get('emoji', '👤')
    else:
        uid = user[0]
        uname = user[1]
        uemoji = user[2] if len(user) > 2 and user[2] is not None else '👤'
    
    if card_action == 'baggage':
        await rq.delete_baggage_card(room.chat_id)
        await update_info(bot, players, room)
        msg_id = (await retry_after_decorate(message.answer)(
            text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
                 f'<b><i>Согласно карте действий игрока [{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>, '
                 f'Весь открытый багаж уничтожен.</i></b>', parse_mode="HTML")).message_id
        room.round_msg.append(msg_id)
        
    elif card_action == 'profession':
        await rq.revers_profession(room.chat_id)
        await update_info(bot, players, room)
        msg_id = (await retry_after_decorate(message.answer)(
            text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
                 f'<b><i>Согласно карте действий игрока [{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>, '
                 f'Профессии всех активных игроков были перемешаны.</i></b>', parse_mode="HTML")).message_id
        room.round_msg.append(msg_id)
        
    elif card_action == 'health':
        res = await rq.update_health(uid, room.chat_id)
        await update_info(bot, [uid, res[2][0]], room)
        msg_id = (await retry_after_decorate(message.answer)(
            text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
                 f'<b><i>Игрок [{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a> '
                 f'передал свое здоровье другому игроку после изгнания\n\n'
                 f'Новые значения характеристики 🫀 Здоровье игрока [{res[2][2]}]<a href="tg://user?id={res[2][0]}">{html.escape(res[2][1])}</a>: '
                 f'<u>{res[1]}</u></i></b>', parse_mode='HTML')).message_id
        room.round_msg.append(msg_id)
        
    elif card_action == 'room':
        if room.bunker['rooms']:
            delete_room = random.choice(room.bunker['rooms'])
            room.bunker['rooms'].remove(delete_room)
            msg_id = (await retry_after_decorate(message.answer)(
                text=f'<blockquote>🃏———<b><i><u>КАРТА ДЕЙСТВИЯ</u></i></b>———🃏</blockquote>'
                     f'<b><i>Согласно карте действий игрока [{uemoji}] <a href="tg://user?id={uid}">{html.escape(uname)}</a>, '
                     f'Одна комната {delete_room} была уничтожена</i></b>', parse_mode='HTML')).message_id
            room.round_msg.append(msg_id)


async def update_info(bot: Bot, users, room: Room):
    for uid in users:
        uid = int(uid)
        if uid not in room.players_dict:
            continue
            
        msg_start = room.players_dict[uid].get('msg_start')
        if not msg_start:
            continue
            
        player_info = await rq.get_player_by_id(uid)
        card1 = await rq.get_player_card(uid)
        
        def get_val(item): return str(item).split('_')[-1] if item else 'Неизвестно'
        
        card_parts = card1.split('_') if card1 else []
        card_desc = await rq.get_card(f"{card_parts[-2]}_{card_parts[-1]}") if len(card_parts) >= 2 else "Нет карты"
        
        text = (f'⚠️ Катастрофа: <b><i><u>{get_val(player_info[6])}</u></i></b>\n\n'
                f'♦️ <b>Ваши характеристики:</b>\n\n'
                f'<blockquote>💼 Профессия: {get_val(player_info[0])}</blockquote>\n'
                f'<blockquote>👤 Био информация: {get_val(player_info[1])}</blockquote>\n'
                f'<blockquote>🫀 Здоровье: {get_val(player_info[2])}</blockquote>\n'
                f'<blockquote>🧩 Хобби: {get_val(player_info[3])}</blockquote>\n'
                f'<blockquote>🎒 Багаж: {get_val(player_info[4])}</blockquote>\n'
                f'<blockquote>✳ Доп. информация: {get_val(player_info[5])}</blockquote>\n'
                f'<blockquote>🕷 Фобия: {get_val(player_info[7])}</blockquote>\n'
                f'<blockquote>💊 Зависимость: {get_val(player_info[8])}</blockquote>\n'
                f'<blockquote>😎 Черта характера: {get_val(player_info[9])}</blockquote>\n\n'
                f'<blockquote>🃏 Карта действия №1: {card_desc}</blockquote>')
                
        try:
            await retry_bad_decorate(bot.edit_message_text)(
                message_id=msg_start, chat_id=uid, text=text,
                reply_markup=await kb.play_info(card1 if card1 and not card1.startswith('open_') else None),
                parse_mode='HTML')
        except aiogram.exceptions.TelegramBadRequest:
            pass