import os.path
import html, random, datetime
from APP.Middlewares.throttling_middleware import flag_default, ThrottlingMiddleware
from APP.Game.Classes import Room
from zoneinfo import ZoneInfo
from config import rooms, user_state, admin_id, dp
import APP.BaseFunc.updates as up
from aiogram.fsm.context import FSMContext
import APP.BaseFunc.requests as rq
import APP.BaseFunc.keyboards as kb
from APP.Middlewares.decorators import retry_after_decorate, retry_bad_decorate
from aiogram.filters import CommandStart, Command
from APP.Game.func import group_start, PlayerState
from APP.Game.requests import close_room_db, close_rooms
from aiogram import F, Router, Bot
from aiogram.types.input_file import FSInputFile, BufferedInputFile
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from APP.Game.func import chats_anti_flood_list
from aiogram.types import Message, CallbackQuery

router = Router()

router.callback_query.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                                      throttle_time_end=4, throttle_time_other=1,
                                                      throttle_time_card=4))
router.message.middleware(ThrottlingMiddleware(throttle_time_open=4, throttle_time_votes=4,
                                               throttle_time_end=4, throttle_time_other=1,
                                               throttle_time_card=4))


@router.message(Command('db'), F.from_user.id == admin_id, flags=flag_default)
async def cmd_download_db(message: Message):
    # Безопасное создание файла в оперативной памяти (без зависания жесткого диска)
    user_ids = await rq.get_user_id()
    content = "\n".join([str(uid[0]) for uid in user_ids]).encode('utf-8')
    
    users_file = BufferedInputFile(content, filename='user_ids.txt')
    await retry_after_decorate(message.answer_document)(document=users_file)


@router.message(CommandStart(), F.from_user.id == F.chat.id, flags=flag_default)
async def cmd_start(message: Message, bot: Bot):
    state = await user_state(message.from_user.id, bot.id)
    new_user = await rq.set_user(message.from_user.id, f"{message.from_user.first_name}")
    if new_user:
        await up.new_user(bot=bot, message=message)
        
    args = message.text.split(' ')
    if len(args) == 2 and args[1][1:].isdigit():
        user_game = await rq.user_game(message.from_user.id)
        room_id = int(args[1])
        room: Room | None = rooms.get(room_id)
        
        if room is not None:
            # ИСПРАВЛЕНО: Теперь бот проверяет, есть ли юзер в оперативной памяти (players_dict)
            if user_game == room_id and message.from_user.id in room.players_dict:
                await retry_after_decorate(message.answer)(
                    text='Вы уже присоединились к этой игре!', message=message)
            elif user_game is not None and user_game != room_id:
                await message.answer(text='Вы не можете присоединиться к нескольким играм одновременно,'
                                          ' дождитесь завершения активной игры!')
            elif room.state == 'start_register' and room.players == room.settings.max_players:
                await message.answer(text='К игре присоединилось максимальное количество игроков!')
            elif room.state == 'start_register' and room.players < room.settings.max_players:
                await state.set_state(PlayerState.in_game)
                await state.update_data(chat_id=room_id)
                await group_start(message, bot, room)
            else:
                await message.answer(text='Игра уже началась, вы не можете присоединиться к комнате!')
        else:
            await message.answer(text='Игра не найдена!')
            
    elif len(args) == 2 and args[1] == 'gift':
        invite_number = await rq.get_invite_number()
        if invite_number < 1500:
            await message.answer(text=f'<b>На данный момент общее количество рефералов: {invite_number}/1500\n\n'
                                      f"Пригласи друга по реферальной ссылке и приблизь получение подарка!</b>",
                                 reply_markup=kb.invite, parse_mode='HTML')
        else:
            await message.answer(text=f'<b>🤩 Количество рефералов достигло необходимого количества!'
                                      f"\n🎁 Ожидайте, скоро промокод на премиум будет опубликован в канале.</b>",
                                 reply_markup=kb.channel, parse_mode='HTML')
                                 
    elif len(args) == 2 and args[1] == 'ref_url':
        await message.answer(f'<b><i>🔗 Ваша реферальная ссылка: '
                             f'https://t.me/GroupBunkerbot?start=add-{message.from_user.id}</i></b>',
                             parse_mode='HTML', disable_web_page_preview=True)
    else:
        await message.answer(text=f'<b>👋 Привет, {html.escape(message.from_user.first_name)}!\n\n'
                                  f"Добро пожаловать в BUNKER Online</b>", reply_markup=kb.markup, parse_mode='HTML')


@router.callback_query(F.data == 'check', flags=flag_default)
async def callback_check_welcome(callback: CallbackQuery):
    await callback.message.edit_text(
        text=f'<b>👋 Привет, {html.escape(callback.from_user.first_name)}!\n\n'
             'Добро пожаловать в BUNKER Online</b>', reply_markup=kb.markup, parse_mode='HTML')


@router.message(Command(commands=['gift']))
async def cmd_gift(message: Message):
    invite_number = await rq.get_invite_number()
    if invite_number < 1500:
        await message.answer(text=f'<b>На данный момент общее количество рефералов: {invite_number}/1500\n\n'
                                  f"Пригласи друга по реферальной ссылке и приблизь получение подарка!</b>",
                             reply_markup=kb.invite, parse_mode='HTML')
    else:
        await message.answer(text=f'<b>🤩 Количество рефералов достигло необходимого количества!'
                                  f"\n🎁 Ожидайте, скоро промокод на премиум будет опубликован в канале.</b>",
                             reply_markup=kb.channel, parse_mode='HTML')


@router.callback_query(F.data == 'invite')
async def callback_invite_ref(callback: CallbackQuery):
    await callback.message.edit_text(
        f'<b><i>🔗 Ваша реферальная ссылка: '
        f'https://t.me/GroupBunkerbot?start=add-{callback.from_user.id}</i></b>',
        parse_mode='HTML', disable_web_page_preview=True)


########################################################################################################################
#                                                   ПРАВИЛА ИГРЫ                                                       #
########################################################################################################################


@router.callback_query(F.data == 'votes_info_in_play', flags=flag_default)
async def callback_votes_info_in_play(callback: CallbackQuery):
    await retry_after_decorate(callback.message.edit_text)(
        text=f"🧐 Как работает голосование?\n \n"
             f"🔸Если число игроков с макс. кол-вом голосов равно "
             f"одному, голосование завершается, игрок покидает игру.\n \n"
             f"🔸Если число игроков с макс. кол-вом голосов больше одного, бот выбирает одного из"
             f" игроков с макс. кол-вом голосов и выгоняет его.",
        reply_markup=kb.send_votes_info)


@router.callback_query(F.data == 'rules1', flags=flag_default)
async def callback_rules1(callback: CallbackQuery):
    await retry_after_decorate(callback.message.edit_text)(
        text=f"1️⃣ Введение\n \n👥 Все игроки узнают, какая случилась катастрофа и получают"
             f" карты с характеристиками своего персонажа.\n \n▶️ На старте игрок "
             f"обезличен и вживается в своего персонажа постепенно, с каждым кругом.\n \n"
             f"👤 У него нет пола, возраста и других категорий, пока он не откроет перед "
             f"всеми игроками соответствующую характеристику.", reply_markup=kb.rules_markup1)


@router.callback_query(F.data == 'rules2', flags=flag_default)
async def callback_rules2(callback: CallbackQuery):
    await retry_after_decorate(callback.message.edit_text)(
        text=f"2️⃣ Игровой круг\n \n🗣 Каждый игрок по очереди открывает одну из своих карт"
             f" и обосновывает, почему именно он должен попасть в бункер.\n \n🎓 В первый "
             f"ход обязательно вскрывается Профессия игрока, во всех остальных на выбор "
             f"игрока.\n \n🔃 Все игроки высказываются по очереди.\n \n⚠ Важно в каждом"
             f" круге оперировать только открытыми характеристиками, так как мы еще много"
             f" чего не знаем о остальных персонажах.", reply_markup=kb.rules_markup2)


@router.callback_query(F.data == 'rules3', flags=flag_default)
async def callback_rules3(callback: CallbackQuery):
    await retry_after_decorate(callback.message.edit_text)(
        text=f"3️⃣ Голосование\n \n"
             f"🗣 После того как все игроки озвучили свои карты, время выдвинуть"
             f" кандидатов на выбывание.Далее проходит общее голосование, и один из "
             f"персонажей теряет право попасть в бункер.\n \n4️⃣ Заключение\n \n🌏Когда "
             f"остается столько же игроков, сколько мест в бункере, двери закрываются. "
             f"Оставшиеся игроки победили!\n \n"
             f"🍀 Хороших вам игр!", reply_markup=kb.rules_markup3)


@router.callback_query(F.data == 'projects', flags=flag_default)
async def callback_projects(callback: CallbackQuery):
    await retry_after_decorate(callback.message.edit_text)(
        text=f'<b>🤝 ПРОЕКТЫ ДРУЗЕЙ:\n \n</b><blockquote>✏️ <b><i><a '
             f'href="https://t.me/ViktorinaOnlineBot/start">Викторины</a></i></b>'
             f'</blockquote>\n \n<i>Больше ботов пока нет...</i>',
        reply_markup=kb.projects, parse_mode='HTML', disable_web_page_preview=True)


@router.callback_query(F.data == 'delete', flags=flag_default)
async def callback_delete_msg(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == 'my_statistics', flags=flag_default)
async def callback_my_statistics(callback: CallbackQuery):
    statistics = await rq.select_victory_defeat(callback.from_user.id)
    win_rate_text = f"Процент побед составляет: {statistics[2] * 100}%" if statistics[2] != 0 else "Вы еще не победили ни в одной игре.\nИграйте и прорывайтесь на вершину!"
    
    await retry_after_decorate(callback.message.edit_text)(
        text="Ваша статистика:\n \n"
             f"🪙 Монет: {statistics[3]}\n"
             f"🏆 Побед:    {statistics[0]}\n"
             f"😵 Поражений:    {statistics[1]}\n \n"
             f"{win_rate_text}",
        reply_markup=kb.back)


@router.callback_query(F.data == 'leaders', flags=flag_default)
async def callback_leaders(callback: CallbackQuery):
    leaders = await rq.leaders()
    lines = ['Топ-10 игроков по проценту побед: \n \n<code>']
    
    for i, leader in enumerate(leaders):
        name = leader[0][:14]
        percentage_str = f"{leader[1]}%"
        lines.append(f"{i+1}. {name}: {percentage_str.rjust(24 - len(name))}")
        
    lines.append("</code>\nИграйте и прорывайтесь на вершину рейтинга!")
    text = "\n".join(lines)
    
    await retry_after_decorate(callback.message.edit_text)(
        text=text, reply_markup=kb.back, parse_mode='HTML')


@router.message(F.chat.id.in_(chats_anti_flood_list), F.chat.id.in_(rooms))
async def filter_msg_del(message: Message, bot: Bot):
    if message.from_user.id == bot.id or message.chat.id == message.from_user.id:
        return
        
    room: Room = rooms[message.chat.id]
    try:
        status = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
        if status.status not in ('administrator', 'creator'):
            if room.state != 'start_register':
                # Проверяем, жив ли игрок в игре, или его вообще там нет
                if (message.from_user.id in room.players_dict and room.players_dict[message.from_user.id]['active'] == 0) or \
                   message.from_user.id not in room.players_dict:
                    await message.delete()
    except TelegramAPIError:
        pass # Игнорируем ошибку, если у бота нет прав удалять сообщения


@router.message(Command(commands=['bd_file']), F.chat.id == admin_id)
async def cmd_bd_file(message: Message):
    if os.path.exists('db.sqlite3'):
        sqlite_file = FSInputFile(os.path.abspath('db.sqlite3'))
        await retry_after_decorate(message.answer_document)(document=sqlite_file)
    else:
        await message.answer("Файл базы данных не найден!")


@router.message(Command(commands=['bonus']), F.chat.id == F.from_user.id, flags=flag_default)
async def cmd_bonus(message: Message, bot: Bot):
    try:
        user_status = (await bot.get_chat_member(chat_id=-1002327143613, user_id=message.from_user.id)).status
        is_subscribed = user_status in ('administrator', 'creator', 'member')
    except TelegramAPIError:
        is_subscribed = False

    if is_subscribed:
        use_bonus = await rq.state_bonus(message.from_user.id)
        if use_bonus:
            await retry_after_decorate(message.answer)(
                text=f'<b>😉 Вы уже получили награду сегодня!\n'
                     f'<i>Возвращайтесь завтра и получите ещё!\n\n'
                     f'🥇 Проявляйте активность в чате и получайте монетки за победу в мини играх!</i></b>',
                parse_mode='HTML', reply_markup=kb.chat)
        else:
            reward = random.randint(10, 40)
            await rq.reward_money(reward, message.from_user.id)
            await rq.use_bonus(message.from_user.id)
            await retry_after_decorate(message.answer)(
                text=f'<b>Вам начислено {reward} монет 🪙\n\n'
                     f'🥇 Проявляйте активность в чате и получайте монетки за победу в мини играх!</b>',
                parse_mode='HTML', reply_markup=kb.chat)
    else:
        await retry_after_decorate(message.answer)(
            text=f'<b>😉 Чтоб получить бонус, пожалуйста, подпишитесь на канал</b>',
            reply_markup=kb.bonus,
            parse_mode='HTML')


@router.callback_query(F.data == 'check_bonus', F.from_user.id == F.message.chat.id, flags=flag_default)
async def callback_check_bonus(callback: CallbackQuery, bot: Bot):
    try:
        user_status = (await bot.get_chat_member(chat_id=-1002327143613, user_id=callback.from_user.id)).status
        is_subscribed = user_status in ('administrator', 'creator', 'member')
    except TelegramAPIError:
        is_subscribed = False

    if is_subscribed:
        use_bonus = await rq.state_bonus(callback.from_user.id)
        if use_bonus:
            await retry_after_decorate(callback.message.answer)(
                text=f'<b>😉 Вы уже получили награду сегодня!\n'
                     f'<i>Возвращайтесь завтра и получите ещё!\n\n'
                     f'🥇 Проявляйте активность в чате и получайте монетки за победу в мини играх!</i></b>',
                parse_mode='HTML', reply_markup=kb.chat)
        else:
            reward = random.randint(10, 40)
            await rq.reward_money(reward, callback.from_user.id)
            await rq.use_bonus(callback.from_user.id)
            await retry_after_decorate(callback.message.edit_text)(
                text=f'<b>🤝 Спасибо за подписку!\nВам начислено {reward} монет 🪙\n\n'
                     f'🥇 Проявляйте активность в чате и получайте монетки за победу в мини играх!</b>',
                parse_mode='HTML', reply_markup=kb.chat)
    else:
        await retry_after_decorate(callback.answer)(
            text=f'💢 Вы не подписались на канал',
            show_alert=True)


@router.message(F.chat.id.in_([-1002180937306]), Command(commands=['reward']))
async def cmd_reward(message: Message, bot: Bot):
    # ЗАЩИТА ОТ КРАША: Если команда вызвана не ответом на сообщение
    if not message.reply_to_message:
        await message.answer("❗️ Эта команда должна использоваться только как 'ответ' (Reply) на сообщение пользователя!")
        return

    try:
        status = await bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
        is_admin = status.status in ('administrator', 'creator')
    except TelegramAPIError:
        is_admin = False

    if is_admin:
        money = [x for x in message.text.split(' ') if x != '']
        if len(money) == 2 and money[1].isdigit():
            reward_amount = int(money[1])
            if reward_amount < 31:
                await rq.reward_money(reward_amount, message.reply_to_message.from_user.id)
                await message.answer(text=f'🏆 <b><i><a href="tg://user?id={message.reply_to_message.from_user.id}">'
                                          f'{html.escape(message.reply_to_message.from_user.first_name)}</a> '
                                          f'получает {reward_amount} монет 🪙</i></b>',
                                     parse_mode='HTML')
            else:
                await message.answer(text=f'<b><i>❗️ Максимальная награда 30 монет 🪙</i></b>', parse_mode='HTML')


chats_premium = []


@router.message(F.chat.id != F.from_user.id, Command(commands=['new_year']))
async def cmd_new_year_promo(message: Message):
    date = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
    if date.year == 2026 and date.month == 1:
        status = await rq.premium(message.chat.id)
        if status == 'default':
            await message.answer(text=f'🏆 <b>Подписка активирована. Вы имеете доступ к премиум настройкам.\n\n'
                                      f'Чтоб установить свои характеристики используйте команду /settings\n\n'
                                      f'Окончание действия подписки: 2026-02-01\n\n'
                                      f'По всем вопросам: @Botbunker</b>',
                                 parse_mode='HTML')
        else:
            await message.answer(text=f'<b>Подписка в вашем чате уже активирована.</b>\n\n',
                                 parse_mode='HTML')
    else:
        await message.answer(text=f'<b>Действие промокода уже завершено.</b>\n\n',
                             parse_mode='HTML')


@router.message(F.chat.id == admin_id, Command(commands=['not_premium']))
async def cmd_not_premium_revoke(message: Message, bot: Bot):
    for chat_id in chats_premium:
        await rq.not_premium(chat_id)
        await retry_after_decorate(bot.send_message)(
            chat_id=chat_id,
            text=f'<b>❗️ Действие подписки закончено.\nВы можете продлить подписку по скидке в течение 5 дней.\n\n'
                 f'Стоимость: <s>300</s> 200р\n'
                 f'Для продления обратитесь к @Botbunker</b>',
            parse_mode='HTML')
    
    await retry_after_decorate(bot.send_message)(
        chat_id=admin_id,
        text=f'Подписки деактивированы',
        parse_mode='HTML')


@router.message(Command('bot_stop_polling'), F.from_user.id == admin_id, flags=flag_default)
async def cmd_stop_polling(message: Message, bot: Bot):
    # Копируем значения, чтобы избежать ошибки при изменении словаря во время итерации
    for room in list(rooms.values()):
        await retry_bad_decorate(bot.send_message)(
            chat_id=room.chat_id,
            parse_mode='HTML',
            text='<blockquote>❗️——<b><i><u>ТЕХНИЧЕСКИЕ РАБОТЫ</u></i></b>——❗️</blockquote>\n\n'
                 '<b>Бот остановлен на технические работы. Игра завершена.\n\n'
                 'Всем игрокам начислено по 30 монет 🪙</b>'
        )
        for player in room.players_dict.values():
            await rq.reward_stop_game(player['user_id'])
            for msg in [player.get('msg_start'), player.get('msg_edit')]:
                if msg is not None:
                    await retry_bad_decorate(bot.delete_message)(chat_id=player['user_id'], message_id=msg)
            
            state: FSMContext = await user_state(player['user_id'], bot.id)
            await state.clear()
            
        await close_room_db(room.chat_id)
        
    await close_rooms()
    rooms.clear()
    await retry_after_decorate(bot.send_message)(chat_id=int(admin_id), text='ЗАВЕРШЕНИЕ РАБОТЫ...')
    await dp.stop_polling()
