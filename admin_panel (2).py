from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile
from config import ADMIN_IDS

# Импортируем модули из нашей папки Admin
from Admin import requests
from Admin import keyboards

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    # Запрашиваем статистику через выделенный файл запросов
    stats = await requests.get_admin_stats()

    text = (
        "📊 <b>АДМИН ПАНЕЛЬ</b>\n"
        "➖➖➖➖➖➖➖➖➖➖\n\n"
        "👥 <b>Пользователи (ЛС):</b>\n"
        f"• Всего: <b>{stats['users_total']}</b>\n"
        f"• Активных: {stats['users_active']} (✅)\n"
        f"• Заблок. бот: {stats['users_inactive']} (🚫)\n"
        "📅 <i>За сегодня:</i>\n"
        f"  ➕ Новых: {stats['users_new_today']}\n"
        f"  ❌ Заблокировали: {stats['users_blocked_today']}\n\n"
        
        "💬 <b>Чаты (Группы):</b>\n"
        f"• Всего добавлено: <b>{stats['chats_total']}</b>\n"
        f"• Активных: {stats['chats_active']} (✅)\n"
        f"• Удалили бота: {stats['chats_inactive']} (🚫)\n"
        "📅 <i>За сегодня:</i>\n"
        f"  ➕ Новых: {stats['chats_new_today']}\n"
        f"  ❌ Удалили: {stats['chats_blocked_today']}"
    )
    
    await message.answer(text, reply_markup=keyboards.admin_main_menu(), parse_mode="HTML")

@admin_router.callback_query(F.data == "admin_refresh")
async def refresh_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    stats = await requests.get_admin_stats()

    text = (
        "📊 <b>АДМИН ПАНЕЛЬ</b>\n"
        "➖➖➖➖➖➖➖➖➖➖\n\n"
        "👥 <b>Пользователи (ЛС):</b>\n"
        f"• Всего: <b>{stats['users_total']}</b>\n"
        f"• Активных: {stats['users_active']} (✅)\n"
        f"• Заблок. бот: {stats['users_inactive']} (🚫)\n"
        "📅 <i>За сегодня:</i>\n"
        f"  ➕ Новых: {stats['users_new_today']}\n"
        f"  ❌ Заблокировали: {stats['users_blocked_today']}\n\n"
        
        "💬 <b>Чаты (Группы):</b>\n"
        f"• Всего добавлено: <b>{stats['chats_total']}</b>\n"
        f"• Активных: {stats['chats_active']} (✅)\n"
        f"• Удалили бота: {stats['chats_inactive']} (🚫)\n"
        "📅 <i>За сегодня:</i>\n"
        f"  ➕ Новых: {stats['chats_new_today']}\n"
        f"  ❌ Удалили: {stats['chats_blocked_today']}"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboards.admin_main_menu(), parse_mode="HTML")
        await callback.answer("Данные обновлены ✅")
    except Exception:
        await callback.answer("Данные не изменились", show_alert=False)

@admin_router.callback_query(F.data == "admin_export_ids")
async def export_ids_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    ids = await requests.get_all_ids()
    if not ids:
        await callback.answer("База данных пуста.", show_alert=True)
        return
        
    # Преобразуем список ID в строку с переносами и кодируем в байты
    file_content = "\n".join(str(id) for id in ids).encode('utf-8')
    document = BufferedInputFile(file_content, filename="all_ids.txt")
    
    await callback.message.answer_document(
        document, 
        caption=f"📁 <b>Файл со всеми ID</b>\n(Пользователи и Группы)\nВсего записей: {len(ids)}",
        parse_mode="HTML"
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_close")
async def close_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

@admin_router.message(Command("export_ids"))
async def cmd_export_ids(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    ids = await requests.get_all_ids()
    if not ids:
        await message.answer("База данных пуста.")
        return
        
    file_content = "\n".join(str(id) for id in ids).encode('utf-8')
    document = BufferedInputFile(file_content, filename="all_ids.txt")
    
    await message.answer_document(
        document, 
        caption=f"📁 <b>Файл со всеми ID</b>\n(Пользователи и Группы)\nВсего записей: {len(ids)}",
        parse_mode="HTML"
    )

@admin_router.message(Command("ad_stat"))
async def cmd_ad_stat(message: types.Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return

    if not command.args:
        await message.answer("Укажите название кампании, например: <code>/ad_stat invite</code>", parse_mode="HTML")
        return

    campaign_name = command.args.strip()
    stats = await requests.get_ad_campaign_stats(campaign_name)
    total = stats['total']
    
    if total == 0:
        await message.answer(f"❌ Кампания <b>{campaign_name}</b> не найдена или данных нет.", reply_markup=keyboards.admin_close_kb(), parse_mode="HTML")
        return

    # Формирование отчета
    text = f"📊 Статистика: <b>{campaign_name}</b>\n"
    text += f"👥 Всего новых пользователей: <b>{total}</b>\n"
    text += "➖➖➖➖➖➖➖➖➖➖\n"
    
    # География (Язык)
    text += "🌍 <b>География (по языку):</b>\n"
    sorted_langs = sorted(stats['langs'].items(), key=lambda item: item[1], reverse=True)
    other_count = 0
    
    for i, (lang, count) in enumerate(sorted_langs):
        percent = round((count / total) * 100)
        if i < 5: # Топ 5 языков
            text += f"• {lang}: {percent}%\n"
        else:
            other_count += count
            
    if other_count > 0:
        other_percent = round((other_count / total) * 100)
        text += f"• Другие: {other_percent}%\n"
        
    text += "\n"
    
    # Демография (Пол)
    genders = stats['genders']
    text += "👤 <b>Демография:</b>\n"
    text += f"• Мужчины: {round((genders['male'] / total) * 100)}%\n"
    text += f"• Женщины: {round((genders['female'] / total) * 100)}%\n"
    text += f"• Не определено: {round((genders['unknown'] / total) * 100)}%\n"

    await message.answer(text, reply_markup=keyboards.admin_close_kb(), parse_mode="HTML")