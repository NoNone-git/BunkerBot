import time
from sqlalchemy import text
from APP.Database.models import engine


async def go_ad_users(ad_date):
    async with engine.begin() as conn:
        # Используем scalar() для безопасного извлечения одного значения
        res = await conn.scalar(text("SELECT start_ad FROM table_ad WHERE ad_date = :ad_date"),
                                {'ad_date': ad_date})
        await conn.execute(text("UPDATE table_ad SET start_ad = 1 WHERE ad_date = :ad_date"),
                           {'ad_date': ad_date})
    return res


async def go_ad_group(ad_date):
    async with engine.begin() as conn:
        res = await conn.scalar(text("SELECT start_group_ad FROM table_ad WHERE ad_date = :ad_date"),
                                {'ad_date': ad_date})
        await conn.execute(text("UPDATE table_ad SET start_group_ad = 1 WHERE ad_date = :ad_date"),
                           {'ad_date': ad_date})
    return res


async def select_ad_post(ad_id=None, ad_date=None):
    async with engine.connect() as conn:
        # Выбираем, по какому полю искать
        if ad_id is not None:
            where_clause = "ad_id = :val"
            val = ad_id
        else:
            where_clause = "ad_date = :val"
            val = ad_date

        # .mappings() автоматически превращает ответ БД в словарь по названиям колонок!
        res = (await conn.execute(
            text(f"SELECT ad_date, ad_text, ad_button, ad_photo, ad_id, ad_animation, "
                 f"ad_sticker, ad_button_callback FROM table_ad WHERE {where_clause}"),
            {'val': val}
        )).mappings().fetchone()

        if res:
            # Очищаем словарь от значений None (как было в твоей изначальной логике)
            return {k: v for k, v in res.items() if v is not None}
        return False


async def update_ad_post(ad_id, ad_date, ad_text, ad_button, ad_photo):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE table_ad SET ad_date = :ad_date, ad_text = :ad_text, "
                 "ad_button = :ad_button, ad_photo = :ad_photo WHERE ad_id = :ad_id"),
            {'ad_id': ad_id, 'ad_date': ad_date, 'ad_text': ad_text, 'ad_button': ad_button,
             'ad_photo': ad_photo}
        )


async def insert_ad_post(ad_date, ad_text, ad_button, ad_photo, ad_animation, ad_sticker, ad_button_callback):
    async with engine.begin() as conn:
        max_id = await conn.scalar(text("SELECT MAX(ad_id) FROM table_ad"))
        ad_id = int(max_id) + 1 if max_id is not None else 1

        # Избавились от опасных f-строк! SQLAlchemy сама безопасно заменит None на NULL
        await conn.execute(
            text("INSERT INTO table_ad(ad_id, ad_date, ad_text, ad_button, ad_photo, ad_animation, ad_sticker, ad_button_callback) "
                 "VALUES(:ad_id, :ad_date, :ad_text, :ad_button, :ad_photo, :ad_animation, :ad_sticker, :ad_button_callback)"),
            {
                'ad_id': ad_id, 'ad_date': ad_date, 'ad_text': ad_text, 'ad_button': ad_button,
                'ad_photo': ad_photo, 'ad_animation': ad_animation, 'ad_sticker': ad_sticker, 
                'ad_button_callback': ad_button_callback
            }
        )
        return ad_id


async def insert_ad_end_post(ad_date, ad_text, ad_button):
    async with engine.begin() as conn:
        max_id = await conn.scalar(text("SELECT MAX(ad_id) FROM end_game_ad"))
        ad_id = int(max_id) + 1 if max_id is not None else 1

        await conn.execute(
            text("INSERT INTO end_game_ad(ad_id, ad_date, ad_text, ad_button) "
                 "VALUES(:ad_id, :ad_date, :ad_text, :ad_button)"),
            {'ad_id': ad_id, 'ad_date': ad_date, 'ad_text': ad_text, 'ad_button': ad_button}
        )
        return ad_id


async def select_ad_end_post(ad_id=None, ad_date=None):
    async with engine.connect() as conn:
        if ad_id is not None:
            where_clause = "ad_id = :val"
            val = ad_id
        else:
            where_clause = "ad_date = :val"
            val = ad_date

        res = (await conn.execute(
            text(f"SELECT ad_date, ad_text, ad_button, ad_id FROM end_game_ad WHERE {where_clause}"),
            {'val': val}
        )).mappings().fetchone()

        if res:
            return {k: v for k, v in res.items() if v is not None}
        
        # Если не нашли, ищем дефолтную рекламу
        res1 = (await conn.execute(
            text("SELECT ad_date, ad_text, ad_button, ad_id FROM end_game_ad WHERE ad_date = 'default'")
        )).mappings().fetchone()

        if res1:
            return {k: v for k, v in res1.items() if v is not None}
        return False


async def all_users_ad():
    async with engine.connect() as conn:
        res = (await conn.execute(text("SELECT user_id FROM users1 WHERE active = 1"))).scalars().all()
    return list(res)


async def all_group_ad():
    async with engine.connect() as conn:
        res_group = (await conn.execute(
            text("SELECT chat_id FROM chats WHERE chat_status <> 'premium' and chat_active = 1")
        )).scalars().all()
    return list(res_group)


async def update_users_in_db(ids):
    start_time = time.time()
    batch_size = 999  # SQLite ограничение

    # Преобразуем в строки на случай, если придут числа
    chat_ids = [str(x) for x in ids if str(x).startswith('-')]
    users_ids = [str(x) for x in ids if not str(x).startswith('-')]

    # Выполняем ВЕСЬ пакет обновлений в одной глобальной транзакции (engine.begin)
    # Это значительно ускорит работу и защитит базу данных!
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE chats SET chat_active = 1"))
        await conn.execute(text("UPDATE users1 SET active = 1"))

        for i in range(0, len(chat_ids), batch_size):
            batch = chat_ids[i:i + batch_size]
            # Безопасное добавление пакета ID через join
            await conn.execute(text(f"UPDATE chats SET chat_active = 0 WHERE chat_id IN ({','.join(batch)})"))

        for i in range(0, len(users_ids), batch_size):
            batch = users_ids[i:i + batch_size]
            await conn.execute(text(f"UPDATE users1 SET active = 0 WHERE user_id IN ({','.join(batch)})"))

    elapsed = time.time() - start_time

    return {
        'time': elapsed,
        'speed': len(ids) / elapsed if elapsed > 0 else 0
    }


async def admin_info():
    async with engine.connect() as conn:
        res_group = await conn.scalar(text("SELECT COUNT(*) FROM chats WHERE chat_active = 1"))
        res_users = await conn.scalar(text("SELECT COUNT(*) FROM users1 WHERE active = 1"))
        users_group = await conn.scalar(text("SELECT SUM(chat_member) FROM chats WHERE chat_active = 1"))
        
    return {
        'users': res_users or 0, 
        'group': res_group or 0, 
        'members': users_group or 0
    }