import os
import re
import aiohttp
import asyncio
from cachetools import TTLCache
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Command
from APP.Middlewares.decorators import retry_after_decorate
from config import admin_id

router = Router()

# Кэш на 3 минуты (180 секунд). Хранит game_data по room_id
ai_game_cache = TTLCache(maxsize=1000, ttl=180)


def get_ai_button(room_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Узнать судьбу бункера 🔮", callback_data=f"ai_end_{room_id}")
    ]])


def format_ai_text(text: str) -> str:
    """Безопасно конвертирует текст от ИИ в HTML для Telegram"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # Зачищаем случайные множественные переносы строк, если ИИ зациклился
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def fetch_ai_story(game_data: dict) -> str:
    API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    MODEL_NAME = os.getenv("AI_MODEL", "gemini-2.5-flash").strip()
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

    if not API_KEY:
        return "⚠️ Ключ GEMINI_API_KEY не настроен в .env файле."

    ai_format = game_data.get('ai_format', 0)

    if ai_format == 0:
        prompt = f"""
        Ты — летописец выжившего человечества. Напиши реалистичную историю о том, что произошло после закрытия дверей бункера.
        
        ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
        1. ЭТО НЕ СИМУЛЯЦИЯ И НЕ ОТЧЕТ. Описывай всё как реальные, свершившиеся исторические события. Никогда не используй слова "симуляция", "отчет", "персонажи".
        2. Пиши информативно, емко и строго по делу. Без лишней воды, сложных метафор и излишней поэтичности. Только реализм и выживание.
        3. Обязательно используй подходящие по смыслу эмодзи (например ☢️💀🌾🔧🔥), чтобы текст был эмоциональным, атмосферным и легче воспринимался визуально.
        4. Заверши рассказ логической точкой. Не обрывай текст. Не используй Markdown-разметку (никаких звездочек).
        5. Ровно 3-4 абзаца.

        🌍 Катастрофа на Земле: {game_data.get('cataclysm', 'Неизвестно')}
        🏕 Бункер: {game_data.get('bunker', 'Обычный бункер')}
        🎲 События до закрытия: {game_data.get('events', 'Без происшествий')}
        
        ✅ ВЫЖИВШИЕ (Они успешно попали внутрь бункера):
        {game_data.get('survivors', 'Нет данных')}
        
        ❌ ИЗГНАННЫЕ (Остались умирать снаружи):
        {game_data.get('kicked', 'Никто не был изгнан')}
        
        План рассказа:
        - Кратко и сурово опиши гибель изгнанных снаружи от условий катастрофы.
        - Расскажи, как выжившие внутри справились с бытом, используя свои профессии и багаж (или как им мешали их болезни/фобии).
        - Оцени возможность продолжения рода: учитывай пол, возраст и плодовитость выживших. Так как нет данных о других уцелевших бункерах, возрождение человеческой популяции зависит только от этих людей. Смогут ли они завести здоровых детей?
        - Подведи конкретный итог: пережили ли они изоляцию, чтобы возродить мир, или человечество вымерло окончательно.
        """
        temp = 0.65
    else:
        prompt = f"""
        Ты — системный ИИ-аналитик. Выдай короткий и ёмкий прогноз выживания группы в бункере.
        
        ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
        1. Максимально коротко (не более 1200 символов, 1-2 ёмких абзаца).
        2. Сухие факты, строгая аналитика и конкретика. Никакой воды, литературы и долгих вступлений. Это краткая выжимка.
        3. Используй немного смысловых эмодзи (✅, ❌, ⚠️, 💀, 🧬).
        4. Логическая точка в конце, без обрывов. Не используй Markdown-разметку.

        🌍 Катастрофа: {game_data.get('cataclysm', 'Неизвестно')}
        🏕 Бункер: {game_data.get('bunker', 'Обычный бункер')}
        🎲 События: {game_data.get('events', 'Без происшествий')}
        
        ✅ ВЫЖИВШИЕ ВНУТРИ:
        {game_data.get('survivors', 'Нет данных')}
        
        ❌ ОСТАЛИСЬ СНАРУЖИ:
        {game_data.get('kicked', 'Никто не был изгнан')}
        
        Структура ответа:
        1. Статус изгнанных (погибли/выжили).
        2. Анализ выживших (навыки/предметы/болезни).
        3. Демографический прогноз: смогут ли они продолжить род (учитывая их пол и плодовитость), ведь других людей на Земле больше нет.
        4. Итог: выжила ли группа и возродилась ли цивилизация.
        """
        temp = 0.5

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temp
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    for attempt in range(2):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, timeout=60) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        try:
                            candidate = data['candidates'][0]
                            raw_text = candidate['content']['parts'][0]['text']
                            finish_reason = candidate.get('finishReason', 'UNKNOWN')
                            
                            # Если текст короче 100 символов - явный сбой генерации, пробуем еще раз
                            if len(raw_text) < 100 and attempt == 0:
                                await asyncio.sleep(1)
                                continue 
                                
                            # Если ИИ все же прервался, дописываем причину для понимания, но текст выводим
                            if finish_reason == 'MAX_TOKENS':
                                raw_text += "\n\n<i>[Конец записи утерян...]</i>"
                                
                            return format_ai_text(raw_text)
                            
                        except (KeyError, IndexError):
                            finish_reason = data.get('candidates', [{}])[0].get('finishReason', 'UNKNOWN')
                            if attempt == 0:
                                await asyncio.sleep(1)
                                continue
                            return f"⚠️ ИИ не смог сформировать ответ. Статус: {finish_reason}"
                    else:
                        if attempt == 0 and resp.status >= 500:
                            await asyncio.sleep(1)
                            continue
                        return f"⚠️ Ошибка генерации (Код {resp.status}): {data.get('error', {}).get('message', '')}"
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            return f"⚠️ Ошибка при подключении к ИИ: {e}"
            
    return "⚠️ Не удалось получить ответ от ИИ после нескольких попыток."


@router.callback_query(F.data.startswith("ai_end_"))
async def callback_ai_ending(callback: CallbackQuery, bot: Bot):
    room_id = int(callback.data.split("_")[2])
    
    if room_id not in ai_game_cache:
        await callback.answer("Время действия предложения истекло", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    game_data = ai_game_cache.pop(room_id)
    
    await retry_after_decorate(callback.message.edit_text)(
        text="<b>Генерирация финала истории на основе ваших решений... Пожалуйста, подождите ⏳</b>", 
        parse_mode="HTML"
    )
    
    story = await fetch_ai_story(game_data)
    
    await retry_after_decorate(callback.message.edit_text)(
        text=f"<b>🌏 Судьба бункера:</b>\n\n{story}",
        parse_mode="HTML"
    )

@router.message(Command("test_ai"), F.from_user.id == admin_id)
async def cmd_test_ai(message: Message):
    # Позволяет писать /test_ai short для теста короткого формата
    parts = message.text.split()
    ai_format = 1 if len(parts) > 1 and parts[1] == 'short' else 0
    
    mock_game_data = {
        'cataclysm': 'Ядерная война. На поверхности бушует радиация и ядерная зима (-50°C).',
        'bunker': 'Заброшенная станция метро. Запасы еды на 5 лет. Есть генератор.',
        'events': 'Из-за короткого замыкания часть проводки сгорела, свет моргает.',
        'survivors': '- Врач-хирург (Био: Девушка 28 лет (плодовитость: Чайлдфри), Здоровье: отличное, Инвентарь: Аптечка)\n- Инженер-электрик (Био: Дед 65 лет (плодовитость: Бесплодность), Багаж: ящик инструментов)',
        'kicked': '- Политик (Болен гриппом)\n- Актер театра (Паническая атака)'
    }
    
    mode_name = "Короткий прогноз" if ai_format == 1 else "Длинный рассказ"
    msg = await message.answer(f"<b>🤖 Отправляю тестовый запрос ({mode_name})... Пожалуйста, подождите ⏳</b>", parse_mode="HTML")
    
    story = await fetch_ai_story(mock_game_data)
    
    await msg.edit_text(f"<b>🔮 Тестовая генерация ИИ:</b>\n\n{story}", parse_mode="HTML")
