import asyncio
import datetime
import os
import html
import re
import APP.Ads.keyboards as kb
import APP.Ads.requests as rq
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.exceptions import (TelegramAPIError, TelegramForbiddenError, 
                                TelegramMigrateToChat, TelegramBadRequest, 
                                TelegramNetworkError)
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery
from config import admin_id

router = Router()


class AdSet(StatesGroup):
    ad_text = State()
    ad_button = State()
    ad_date = State()
    ad_id = State()
    ad_photo = State()
    ad_animation = State()
    ad_sticker = State()
    ad_button_callback = State()
    waiting_for_file = State()
    waiting_for_forward = State()


# === ПАРСЕР ДЛЯ РУЧНОГО ВВОДА КНОПОК ===
def parse_manual_buttons(html_text: str, is_callback: bool = False) -> str:
    rows_str = []
    if not html_text:
        return ""
        
    lines = html_text.split('\n')
    for line in lines:
        if not line.strip():
            continue
            
        row_btns = []
        buttons = line.split('|')
        for btn in buttons:
            # 1. Автоматически извлекаем ID премиум-эмодзи из HTML
            match = re.search(r'<tg-emoji[^>]*emoji-id=["\'](\d+)["\'][^>]*>[^<]*</tg-emoji>', btn)
            auto_emoji_id = match.group(1) if match else None
            
            # 2. Очищаем кнопку от самого премиум эмодзи, чтобы избежать дублирования
            if match:
                btn = re.sub(r'<tg-emoji[^>]*emoji-id=["\']\d+["\'][^>]*>[^<]*</tg-emoji>', '', btn, count=1)
            
            # 3. Очищаем кнопку от всех остальных HTML-тегов, чтобы получить чистый текст для сплита
            clean_btn = re.sub(r'<[^>]+>', '', btn)
            parts = clean_btn.split(' - ')
            
            # 4. Извлекаем Текст (или ставим пустой символ, если кнопка из одних эмодзи)
            btn_text = parts[0].strip() if len(parts) > 0 and parts[0].strip() else "\u200b"
            
            # 5. Извлекаем URL/Callback и Стиль
            btn_arg2 = parts[1].strip() if len(parts) > 1 else ("None" if is_callback else "")
            btn_style = parts[2].strip() if len(parts) > 2 else "0"
            
            # 6. Проверяем, не указал ли админ ID вручную 4-м параметром
            manual_emoji_id = parts[3].strip() if len(parts) > 3 else None
            
            # Приоритет: Авто-Парсинг -> Ручной Ввод -> None
            final_emoji_id = auto_emoji_id or manual_emoji_id or 'None'
            
            row_btns.append(f"{btn_text} - {btn_arg2} - {btn_style} - {final_emoji_id}")
            
        rows_str.append(" | ".join(row_btns))
    return "\n".join(rows_str)
# =======================================


@router.message(Command(commands=['ref_url']))
async def cmd_ref_url(message: Message, bot: Bot):
    await message.answer(f'<b><i>🔗 Ваша реферальная ссылка: '
                         f'https://t.me/GroupBunkerbot?start=add-{message.from_user.id}</i></b>',
                         parse_mode='HTML', disable_web_page_preview=True)


@router.message(Command(commands=['admin_info']), F.chat.id == admin_id)
async def cmd_admin_info(message: Message, bot: Bot):
    admin_info = await rq.admin_info()
    await message.answer(f"<b><i>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЯХ:</i>\n\n"
                         f"Активных групп: {admin_info['group']}\n"
                         f"В группах ≈ {admin_info['members']} участника(ов)\n"
                         f"Активных пользователей: {admin_info['users']}</b>",
                         parse_mode='HTML')


@router.message(Command(commands=['start_ad_users']))
async def cmd_start_ad_users(message: Message, bot: Bot):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        go_ad = await rq.go_ad_users(str(datetime.date.today()))
        data = await rq.select_ad_post(ad_date=str(datetime.date.today()))
        if data and not go_ad:
            users_list_ad = await rq.all_users_ad()
            await start_ad(message, bot, data, users_list_ad)
        else:
            await message.answer('Реклама на сегодня не куплена или уже запущена')


@router.message(Command(commands=['start_ad_group']))
async def cmd_start_ad_group(message: Message, bot: Bot):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        go_ad = await rq.go_ad_group(str(datetime.date.today()))
        data = await rq.select_ad_post(ad_date=str(datetime.date.today()))
        if data and not go_ad:
            group_list_ad = await rq.all_group_ad()
            await start_ad(message, bot, data, group_list_ad)
        else:
            await message.answer('Реклама на сегодня не куплена или уже запущена')


@router.message(Command(commands=['start_ad_promo']))
async def cmd_start_ad_promo(message: Message, bot: Bot):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        go_ad = await rq.go_ad_users('promo')
        data = await rq.select_ad_post(ad_date='promo')
        go_ad_new_year = await rq.go_ad_users('new_year')
        data_new_year = await rq.select_ad_post(ad_date='new_year')
        if not go_ad and not go_ad_new_year:
            users_list_ad = await rq.all_users_ad()
            await start_promo(message, bot, data, data_new_year, users_list_ad)
        else:
            await message.answer('Реклама на сегодня не куплена или уже запущена')


async def start_promo(message: Message, bot: Bot, data, data_new_year, list_ad):
    list_not_ad = []
    number_of_ad = 0
    await message.answer(f"✅ Рассылка promo запущена.\nID: {data['ad_id']}")
    for i, user_id in enumerate(list_ad):
        try:
            ad = await ad_preview(data_new_year, user_id, bot)
            await ad_preview(data, user_id, bot)
        except TelegramAPIError:
            ad = user_id
            
        if ad:
            list_not_ad.append(user_id)
        else:
            number_of_ad += 1
        await asyncio.sleep(0.3)
        
    text = f'{list_not_ad}'
    if len(text) > 4096:
        for x in range(0, len(text), 4000):
            await bot.send_message(chat_id=admin_id, text=text[x:x+4000])
    else:
        await bot.send_message(chat_id=admin_id, text=text)
        
    await message.answer(f"✅ Рассылка завершена.\nID: {data['ad_id']}\nВсего сообщений: {number_of_ad}")


async def start_ad(message: Message, bot: Bot, data, list_ad):
    list_not_ad = []
    number_of_ad = 0
    await message.answer(f"✅ Рассылка запущена.\nID: {data['ad_id']}")
    for i, user_id in enumerate(list_ad):
        try:
            ad = await ad_preview(data, user_id, bot)
        except TelegramAPIError:
            ad = user_id
            
        if ad:
            list_not_ad.append(user_id)
        else:
            number_of_ad += 1
        await asyncio.sleep(0.1)
        
    text = f'{list_not_ad}'
    if len(text) > 4096:
        for x in range(0, len(text), 4000):
            await bot.send_message(chat_id=admin_id, text=text[x:x+4000])
    else:
        await bot.send_message(chat_id=admin_id, text=text)
        
    await message.answer(f"✅ Рассылка завершена.\nID: {data['ad_id']}\nВсего сообщений: {number_of_ad}")


async def ad_preview(data, chat_id, bot: Bot):
    if 'ad_button' in data:
        func_button = kb.ad_button
        date_markup = data['ad_button']
    elif 'ad_button_callback' in data:
        date_markup = data['ad_button_callback']
        func_button = kb.ad_button_callback
    else:
        date_markup = None
        func_button = None
        
    try:
        reply_markup = await func_button(date_markup) if date_markup is not None else None
        
        if 'ad_photo' in data:
            await bot.send_photo(
                photo=data['ad_photo'],
                caption=data.get('ad_text'),
                reply_markup=reply_markup,
                chat_id=chat_id,
                parse_mode='HTML')
        elif 'ad_animation' in data:
            await bot.send_animation(
                animation=data['ad_animation'],
                caption=data.get('ad_text'),
                reply_markup=reply_markup,
                chat_id=chat_id,
                parse_mode='HTML')
        elif 'ad_sticker' in data:
            await bot.send_sticker(
                sticker=data['ad_sticker'],
                reply_markup=reply_markup,
                chat_id=chat_id)
        elif 'ad_text' in data:
            await bot.send_message(
                text=data['ad_text'],
                reply_markup=reply_markup,
                chat_id=chat_id,
                parse_mode='HTML',
                disable_web_page_preview=False)
        return False
        
    except (TelegramForbiddenError, TelegramMigrateToChat):
        return chat_id
    except TelegramBadRequest:
        try:
            if 'ad_text' not in data:
                return chat_id
            reply_markup = await kb.ad_button(data['ad_button']) if 'ad_button' in data else None
            await bot.send_message(
                text=data['ad_text'],
                reply_markup=reply_markup,
                chat_id=chat_id,
                parse_mode='HTML',
                disable_web_page_preview=False)
            return False
        except (TelegramForbiddenError, TelegramMigrateToChat, TelegramBadRequest):
            return chat_id
        except (TelegramNetworkError, TimeoutError) as _ex:
            await asyncio.sleep(5)
            await bot.send_message(chat_id=admin_id, text=f"🍀 Ошибка при отправке рекламы.\n\n{_ex}")
            await ad_preview(data, chat_id, bot)
    except (TelegramNetworkError, TimeoutError) as _ex:
        await asyncio.sleep(5)
        await bot.send_message(chat_id=admin_id, text=f"🍀 Ошибка при отправке рекламы.\n\n{_ex}")
        await ad_preview(data, chat_id, bot)


########################################################################################################################
#                                                 ДЛЯ ПРОВЕРКИ КОДА                                                    #
########################################################################################################################


@router.message(Command(commands=['get_ad']))
async def cmd_get_ad(message: Message, bot: Bot):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            data = await rq.select_ad_post(ad_id=parts[1])
            if data:
                await ad_preview(data, admin_id, bot)
                await message.answer(f"Дата отправки: {data['ad_date']}\nID: {data['ad_id']}")
            else:
                await message.answer('Рекламного поста с таким id нет')


@router.message(Command(commands=['get_end_ad']))
async def cmd_get_end_ad(message: Message, bot: Bot):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            data = await rq.select_ad_end_post(ad_id=parts[1])
            if data:
                await ad_preview(data, admin_id, bot)
                await message.answer(f"Дата отправки: {data['ad_date']}\nID: {data['ad_id']}")
            else:
                await message.answer('Рекламного поста с таким id нет')


@router.message(Command(commands=['set_ad']))
async def cmd_set_ad_start(message: Message):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        await message.answer('Пожалуйста, выберите метод установки. Вы можете переслать уже готовый пост или собрать его вручную:', reply_markup=kb.set_ad_start)


# === ЛОГИКА ПЕРЕСЫЛКИ СООБЩЕНИЯ (ПОЛНЫЙ ПАРСИНГ) ===
@router.callback_query(F.data == 'set_ad_forward')
async def callback_ad_forward_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        '🔄 <b>Перешлите мне сообщение (пост) из канала или чата.</b>\n\n'
        'Я автоматически скопирую:\n'
        '— Текст со всеми шрифтами, скрытыми ссылками и <b>премиум-эмодзи</b>\n'
        '— Картинку, анимацию, видео или стикер\n'
        '— Inline-клавиатуру (кнопки, ссылки, стили и их <b>премиум-эмодзи</b>)',
        parse_mode='HTML'
    )
    await state.set_state(AdSet.waiting_for_forward)


@router.message(AdSet.waiting_for_forward)
async def process_ad_forward(message: Message, state: FSMContext, bot: Bot):
    update_dict = {}
    
    # Извлекаем текст (Aiogram 3.x автоматически конвертирует сущности в HTML, включая премиум эмодзи)
    if message.html_text:
        update_dict['ad_text'] = message.html_text
        
    # Извлекаем медиа
    if message.photo:
        update_dict['ad_photo'] = message.photo[-1].file_id
    elif message.animation:
        update_dict['ad_animation'] = message.animation.file_id
    elif message.video:
        update_dict['ad_animation'] = message.video.file_id  # Видео сохраняем как анимацию
    elif message.sticker:
        update_dict['ad_sticker'] = message.sticker.file_id
        
    # Извлекаем клавиатуру и преобразуем в наш текстовый формат с извлечением ID премиум-эмодзи
    if message.reply_markup and message.reply_markup.inline_keyboard:
        rows_url = []
        rows_cb = []
        for row in message.reply_markup.inline_keyboard:
            url_btns = []
            cb_btns = []
            for btn in row:
                text = btn.text.strip() if btn.text else '\u200b'
                if not text: 
                    text = '\u200b'
                
                # Сохраняем стиль, если он есть
                style = getattr(btn, 'style', '0')
                if not style:
                    style = '0'
                    
                # Получаем ID премиум эмодзи, если оно есть внутри кнопки
                emoji_id = getattr(btn, 'icon_custom_emoji_id', 'None')
                if not emoji_id:
                    emoji_id = 'None'
                    
                if btn.url:
                    url_btns.append(f"{text} - {btn.url} - {style} - {emoji_id}")
                elif btn.callback_data:
                    cb_btns.append(f"{text} - {btn.callback_data} - {style} - {emoji_id}")
            
            if url_btns:
                rows_url.append(" | ".join(url_btns))
            if cb_btns:
                rows_cb.append(" | ".join(cb_btns))
                
        if rows_url:
            update_dict['ad_button'] = "\n".join(rows_url)
        if rows_cb:
            update_dict['ad_button_callback'] = "\n".join(rows_cb)

    await state.update_data(**update_dict)
    data = await state.get_data()
    
    await ad_preview(data, message.chat.id, bot)
    await message.answer(
        '✅ <b>Сообщение успешно скопировано!</b>\n\n'
        'Вы можете отредактировать элементы вручную или сразу сохранить.',
        reply_markup=kb.set_ad,
        parse_mode='HTML',
        disable_web_page_preview=True
    )
# ===================================================


@router.callback_query(F.data == 'set_ad_text')
async def callback_ad_text_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Пожалуйста отправьте текст')
    await state.set_state(AdSet.ad_text)


@router.message(AdSet.ad_text)
async def process_ad_text(message: Message, state: FSMContext, bot: Bot):
    # Используем html_text, чтобы премиум-эмодзи и разметка парсились корректно даже при вводе вручную
    await state.update_data(ad_text=message.html_text)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять текст, вышлите его повторно.',
                         parse_mode='HTML', reply_markup=kb.set_ad,
                         disable_web_page_preview=True)


@router.callback_query(F.data == 'set_ad_button')
async def callback_ad_button_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        '1. Отправьте мне список URL-кнопок в одном сообщении.\n'
        'Вы можете использовать <b>премиум-эмодзи</b> прямо в тексте кнопки, бот их автоматически сохранит!\n\n'
        'Формат (Стиль: danger, primary, success - можно пропустить):\n\n'
        '<code>Кнопка 1 - url - primary\n'
        '🙂 - url</code>\n\n'
        '2. Используйте разделитель |, чтобы добавить до трех кнопок в один ряд.\n\n'
        '<code>Кнопка 1 - url | Кнопка 2 - url - danger\n'
        'Кнопка 3 - url | 🙂 - url</code>', 
        parse_mode='HTML'
    )
    await state.set_state(AdSet.ad_button)


@router.message(AdSet.ad_button)
async def process_ad_button(message: Message, state: FSMContext, bot: Bot):
    # Бронебойный парсер HTML-разметки для получения ID премиум эмодзи
    formatted_buttons = parse_manual_buttons(message.html_text, is_callback=False)
    
    await state.update_data(ad_button=formatted_buttons)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять клавиатуру, вышлите её повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_button_callback')
async def callback_ad_button_callback_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        '1. Отправьте мне список callback-кнопок в одном сообщении.\n'
        'Вы можете использовать <b>премиум-эмодзи</b> прямо в тексте кнопки, бот их автоматически сохранит!\n\n'
        'Формат (Стиль: danger, primary, success - можно пропустить):\n\n'
        '<code>Кнопка 1 - callback_data - primary\n'
        '🙂 - callback_data</code>\n\n'
        '2. Используйте разделитель |, чтобы добавить до трех кнопок в один ряд.\n\n'
        '<code>Кнопка 1 - cb_data | Кнопка 2 - cb_data - danger\n'
        'Кнопка 3 - cb_data | 🙂 - cb_data</code>', 
        parse_mode='HTML'
    )
    await state.set_state(AdSet.ad_button_callback)


@router.message(AdSet.ad_button_callback)
async def process_ad_button_callback(message: Message, state: FSMContext, bot: Bot):
    # Бронебойный парсер HTML-разметки для получения ID премиум эмодзи
    formatted_buttons = parse_manual_buttons(message.html_text, is_callback=True)
    
    await state.update_data(ad_button_callback=formatted_buttons)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять клавиатуру, вышлите её повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_photo')
async def callback_ad_photo_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Пожалуйста отправьте ссылку на медиафайл или само фото')
    await state.set_state(AdSet.ad_photo)


@router.message(AdSet.ad_photo)
async def process_ad_photo(message: Message, state: FSMContext, bot: Bot):
    photo_data = message.photo[-1].file_id if message.photo else message.text
    await state.update_data(ad_photo=photo_data)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять фото, вышлите ссылку/фото повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_sticker')
async def callback_ad_sticker_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Пожалуйста отправьте id стикера или сам стикер')
    await state.set_state(AdSet.ad_sticker)


@router.message(AdSet.ad_sticker)
async def process_ad_sticker(message: Message, state: FSMContext, bot: Bot):
    sticker_data = message.sticker.file_id if message.sticker else message.text
    await state.update_data(ad_sticker=sticker_data)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять стикер, вышлите его id/стикер повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_animation')
async def callback_ad_animation_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Пожалуйста отправьте ссылку на анимацию или саму GIF')
    await state.set_state(AdSet.ad_animation)


@router.message(AdSet.ad_animation)
async def process_ad_animation(message: Message, state: FSMContext, bot: Bot):
    animation_data = message.animation.file_id if message.animation else message.text
    await state.update_data(ad_animation=animation_data)
    data = await state.get_data()
    await ad_preview(data, message.chat.id, bot)
    await message.answer('Если хотите поменять анимацию, вышлите ссылку/GIF повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_date')
async def callback_ad_date_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Пожалуйста отправьте дату в формате 2008-01-21')
    await state.set_state(AdSet.ad_date)


@router.message(AdSet.ad_date)
async def process_ad_date(message: Message, state: FSMContext):
    await state.update_data(ad_date=message.text)
    await message.answer(f'Дата {message.text} установлена.\n \n'
                         f'Если хотите поменять дату отправьте её повторно.', reply_markup=kb.set_ad)


@router.callback_query(F.data == 'set_ad_not')
async def callback_cancel_ad(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdSet.ad_id)
    await state.clear()
    await callback.message.answer('Установка рекламы отменена')


@router.callback_query(F.data == 'set_ad_newsletter')
async def callback_save_newsletter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdSet.ad_id)
    data = await state.get_data()
    ad_id = await rq.insert_ad_post(
        data.get('ad_date'), data.get('ad_text'), data.get('ad_button'),
        data.get('ad_photo'), data.get('ad_animation'), 
        data.get('ad_sticker'), data.get('ad_button_callback')
    )
    await callback.message.answer(f'Реклама установлена. id: {ad_id}')
    await state.clear()


@router.callback_query(F.data == 'set_ad_end')
async def callback_save_end_ad(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdSet.ad_id)
    data = await state.get_data()
    ad_id = await rq.insert_ad_end_post(
        data.get('ad_date'), data.get('ad_text'), data.get('ad_button')
    )
    await callback.message.answer(f'Реклама установлена. id: {ad_id}')
    await state.clear()


@router.message(Command("update"))
async def cmd_update_users(message: Message, state: FSMContext):
    if message.from_user.id == admin_id and message.from_user.id == message.chat.id:
        await state.update_data(table=message.text)
        await message.answer(
            "📎 Пожалуйста, отправьте текстовый файл (.txt) с ID пользователей.\n"
            "Каждый ID должен быть на отдельной строке.\n\n"
            "⏳ Обработка может занять некоторое время в зависимости от количества ID."
        )
        await state.set_state(AdSet.waiting_for_file)


@router.message(AdSet.waiting_for_file, F.document)
async def handle_document(message: Message, state: FSMContext, bot: Bot):
    if message.document.mime_type != "text/plain" and not message.document.file_name.endswith('.txt'):
        await message.answer("❌ Пожалуйста, отправьте именно текстовый файл (.txt)")
        return
        
    msg_wait = await message.answer("📥 Скачиваю файл...")
    file_path = f"temp_{message.document.file_id}.txt"
    
    try:
        file_info = await bot.get_file(message.document.file_id)
        await bot.download_file(file_info.file_path, file_path)

        await msg_wait.edit_text("📊 Читаю ID из файла...")
        with open(file_path, 'r', encoding='utf-8') as f:
            ids = [line.strip() for line in f if line.strip()]

        if not ids:
            await msg_wait.edit_text("❌ Файл пуст или содержит только пустые строки")
            return

        await msg_wait.edit_text(f"✅ Найдено {len(ids)} ID\n⚡️ Начинаю обновление...")

        result = await rq.update_users_in_db(ids)

        report = (f"📊 Отчет об обновлении:\n"
                  f"⏱️ Время выполнения: {result['time']:.2f} секунд\n"
                  f"📈 Скорость: {result['speed']:.0f} записей/сек")

        await msg_wait.edit_text(report)

    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await state.clear()