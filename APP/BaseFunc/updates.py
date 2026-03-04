import html
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, MEMBER, ADMINISTRATOR, KICKED

import APP.BaseFunc.updates_requests as rq
import APP.BaseFunc.keyboards as kb
from APP.Middlewares.decorators import retry_after_decorate
from APP.Game.Classes import Room
from config import rooms, log_chat_id, invite_chat_id, admin_id

router = Router()


async def referral_reward():
    pass


async def referral(user_id, bot: Bot, message: Message):
    gift = await rq.invite()
    
    # Безопасное формирование ссылки
    user_link = (f'<a href="t.me/{message.from_user.username}">{html.escape(message.from_user.first_name)}</a>' 
                 if message.from_user.username else html.escape(message.from_user.first_name))
    
    await retry_after_decorate(bot.send_message)(
        chat_id=user_id,
        text=f'<b><i><blockquote> 🔗 ———— НОВЫЙ РЕФЕРАЛ ———— 🔗 </blockquote>\n \n'
             f'🔗 По вашей реферальной ссылке перешел пользователь {user_link}.\n'
             f'</i></b>', 
        parse_mode='HTML',
        disable_web_page_preview=True)
        
    if gift:
        # Заменен захардкоженный ID (7447348212) на переменную admin_id из config
        await retry_after_decorate(bot.send_message)(
            chat_id=admin_id,
            text=f'<b><i><blockquote> 🔗 ———— ОПОВЕЩЕНИЕ ———— 🔗 </blockquote>\n \n'
                 f'Количество рефералов достигло 1500</i></b>', 
            parse_mode='HTML')


async def new_user(message: Message, bot: Bot):
    invite = None
    if message.text:
        parts = message.text.split(' ')
        if len(parts) == 2 and parts[1].startswith('add-'):
            invite_data = parts[1].split('-')[1]
            if invite_data.isdigit():
                invite = invite_data
                await referral(invite, bot, message)

    chat_link = (f'<a href="t.me/{message.chat.username}">{html.escape(message.chat.full_name)}</a>' 
                 if message.chat.username else html.escape(message.chat.full_name))
                 
    inviter_text = f"Пригласил: {invite if str(invite).isdigit() else f'@{invite}'}" if invite else ""

    await retry_after_decorate(bot.send_message)(
        chat_id=invite_chat_id if invite else log_chat_id,
        text=f'➕ Новый пользователь: {chat_link}\n'
             f'Username: @{message.from_user.username}\n'
             f'User_id: {message.from_user.id}\n'
             f'{inviter_text}',
        parse_mode='HTML', 
        disable_web_page_preview=True)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR))
async def on_bot_promoted(event: ChatMemberUpdated, bot: Bot):
    chat_members = await bot.get_chat_member_count(event.chat.id)
    await rq.set_chat(event.chat.id, event.chat.full_name, chat_members, event.chat.username)
    
    chat_link = (f'<a href="t.me/{event.chat.username}">{html.escape(event.chat.full_name)}</a>' 
                 if event.chat.username else html.escape(event.chat.full_name))
    chat_username = f'@{event.chat.username}' if event.chat.username else str(event.chat.username)
    adder_link = (f'<a href="t.me/{event.from_user.username}">{html.escape(event.from_user.full_name)}</a>' 
                  if event.from_user.username else html.escape(event.from_user.full_name))
                  
    await retry_after_decorate(bot.send_message)(
        chat_id=log_chat_id,
        text=f'➕ Бот добавлен в группу в качестве администратора: {chat_link}\n'
             f'Тип: {event.chat.type}\n'
             f'Username: {chat_username}\n'
             f'Chat_id: {event.chat.id}\n'
             f'Members: {chat_members}\n'
             f'Добавил: {adder_link}',
        parse_mode='HTML', disable_web_page_preview=True)
        
    await retry_after_decorate(bot.send_message)(
        chat_id=event.chat.id,
        text='<i><b><blockquote>👋 ————— ПРИВЕТ ————— 👋</blockquote>\n'
             '🎮 Я бот-ведущий игры БУНКЕР.\n \n'
             '📰 Следите за обновлениями в официальном канале.\n \n'
             '🎮 УДАЧНЫХ ИГР! 🎮</b></i>',
        reply_markup=kb.channel_link, parse_mode='HTML')


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
async def on_bot_added(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type == 'private':
        await rq.set_user(event.from_user.id, event.from_user.first_name)
        
        chat_link = (f'<a href="t.me/{event.chat.username}">{html.escape(event.chat.full_name)}</a>' 
                     if event.chat.username else html.escape(event.chat.full_name))
        chat_username = f'@{event.chat.username}' if event.chat.username else str(event.chat.username)
        
        await retry_after_decorate(bot.send_message)(
            chat_id=log_chat_id,
            text=f'➕ Новый пользователь: {chat_link}\n'
                 f'Username: {chat_username}\n'
                 f'User_id: {event.from_user.id}',
            parse_mode='HTML', disable_web_page_preview=True)
    else:
        chat_members = await bot.get_chat_member_count(event.chat.id)
        await rq.set_chat(event.chat.id, event.chat.full_name, chat_members, event.chat.username)
        
        chat_link = (f'<a href="t.me/{event.chat.username}">{html.escape(event.chat.full_name)}</a>' 
                     if event.chat.username else html.escape(event.chat.full_name))
        chat_username = f'@{event.chat.username}' if event.chat.username else str(event.chat.username)
        adder_link = (f'<a href="t.me/{event.from_user.username}">{html.escape(event.from_user.full_name)}</a>' 
                      if event.from_user.username else html.escape(event.from_user.full_name))
                      
        await retry_after_decorate(bot.send_message)(
            chat_id=log_chat_id,
            text=f'➕ Новая группа: {chat_link}\n'
                 f'Тип: {event.chat.type}\n'
                 f'Username: {chat_username}\n'
                 f'Chat_id: {event.chat.id}\n'
                 f'Members: {chat_members}\n'
                 f'Добавил: {adder_link}',
            parse_mode='HTML', disable_web_page_preview=True)
            
        await retry_after_decorate(bot.send_message)(
            chat_id=event.chat.id,
            text='<i><b><blockquote>👋 ————— ПРИВЕТ ————— 👋</blockquote>\n'
                 '🎮 Я бот-ведущий игры БУНКЕР.\n \n'
                 '✅ Чтоб начать игру, пожалуйста, выдайте мне права администратора.\n \n'
                 '📰 Следите за обновлениями в официальном канале.\n \n'
                 '🎮 УДАЧНЫХ ИГР! 🎮</b></i>',
            parse_mode='HTML', reply_markup=kb.channel_link)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def on_bot_kicked(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type == 'private':
        await rq.kicked(event.from_user.id)
    elif event.chat.type in ('group', 'supergroup'):
        await rq.out_chat(event.chat.id)
        room: Room | None = rooms.get(event.chat.id)
        if room is not None:
            await room.close_room(bot=bot)


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_joined_group(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type in ('supergroup', 'group'):
        data = await rq.get_hello_ad()
        if data is None:
            return
            
        try:
            chat_status = await rq.get_chat_status(event.chat.id)
        except TypeError:
            chat_members = await bot.get_chat_member_count(event.chat.id)
            await rq.set_chat(event.chat.id, event.chat.full_name, chat_members, event.chat.username)
            chat_status = 'default'
            
        if chat_status != 'premium':
            user_link = (f'https://t.me/{event.from_user.username}' 
                         if event.from_user.username else f'tg://user?id={event.from_user.id}')
                         
            await retry_after_decorate(bot.send_message)(
                text=f'👋 Привет, <a href="{user_link}">{html.escape(event.from_user.first_name)}</a>. '
                     f'Добро пожаловать в чат!\n \n{data["ad_text"]}',
                reply_markup=await kb.ad_button(data['ad_button']) if 'ad_button' in data else None,
                chat_id=event.chat.id,
                parse_mode='HTML',
                disable_web_page_preview=True)