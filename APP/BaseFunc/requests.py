import sqlalchemy.exc
from APP.Database.models import engine
from sqlalchemy import text
import time


async def insert_db(char_name, char, index):
    async with engine.begin() as conn:
        await conn.execute(
            text(f"INSERT INTO {char_name}(id, {char_name}_name) VALUES (:index, :char)"),
            {'index': index, 'char': char}
        )


async def delete_db(char_name):
    async with engine.begin() as conn:
        await conn.execute(text(f"DELETE FROM {char_name}"))


async def create_db(char_name):
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE TABLE IF NOT EXISTS {char_name}("
                                f"id int not null primary key, "
                                f"{char_name}_name VARCHAR(100) NOT NULL);"))


async def set_user(user_id, name):
    async with engine.begin() as conn:
        res = (await conn.execute(
            text("SELECT name, active FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )).fetchone()
        
        if not res:
            await conn.execute(
                text("INSERT INTO users1 (user_id, name, active) VALUES(:user_id, :name, 1)"),
                {'user_id': user_id, 'name': name}
            )
            return 1
        else:
            if res[0] != name or res[1] != 1:
                await conn.execute(
                    text("UPDATE users1 SET name = :name, active = 1 WHERE user_id = :user_id"),
                    {'name': name, 'user_id': user_id}
                )
            return 0


async def user_game(user_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT room_id FROM users1 WHERE user_id = :user_id"), 
            {'user_id': user_id}
        )


async def select_victory_defeat(user_id):
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT victory, defeat, user_statistics, balance FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )
        return res.fetchone()


async def leaders():
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT name, user_statistics FROM users1 WHERE defeat + victory > 19 "
                 "ORDER BY user_statistics DESC LIMIT 10")
        )
        return res.fetchall()


async def select_chat_settings(chat_id):
    async with engine.connect() as conn:
        chat_settings_str = await conn.scalar(
            text("SELECT chat_settings FROM chats WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )
        
    settings = {}
    if chat_settings_str:
        for el in chat_settings_str.split(' - '):
            key, val = el.split(':', 1)
            if val.isdigit():
                settings[key] = int(val)
            elif val.startswith('bool='):
                settings[key] = bool(int(val.split('=')[1]))
            else:
                settings[key] = str(val)
    return settings


async def select_user_chat_info(user_id):
    async with engine.connect() as conn:
        chat_id = await conn.scalar(
            text("SELECT chat_id from users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )
        if chat_id is not None:
            chat_info = (await conn.execute(
                text("SELECT chat_name, chat_username FROM chats WHERE chat_id = :chat_id"),
                {'chat_id': chat_id}
            )).fetchone()
            if chat_info:
                return [chat_id, chat_info[0], chat_info[1]]
        return None


async def set_user_chat(user_id, chat_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET chat_id = :chat_id WHERE user_id = :user_id"),
            {'user_id': user_id, 'chat_id': chat_id}
        )


async def update_settings(settings_text, chat_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE chats SET chat_settings = :settings_text WHERE chat_id = :chat_id"),
            {'settings_text': settings_text, 'chat_id': chat_id}
        )


async def update_prem_settings(settings_text, chat_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE premium_chats SET chat_settings = :settings_text WHERE chat_id = :chat_id"),
            {'settings_text': settings_text, 'chat_id': chat_id}
        )


async def sql_query(query_type, sql_text):
    try:
        if query_type == 'commit':
            async with engine.begin() as conn:
                await conn.execute(text(sql_text))
            return query_type
        elif query_type == 'select':
            async with engine.connect() as conn:
                result_text = (await conn.execute(text(sql_text))).fetchall()
            return result_text
    except sqlalchemy.exc.SQLAlchemyError as _ex:
        return str(_ex)


async def reward_stop_game(user_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET balance = balance + 30 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def select_prem_char(chat_id, char_type):
    async with engine.connect() as conn:
        return await conn.scalar(
            text(f"SELECT {char_type} from premium_chats WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )


async def select_prem_settings(chat_id):
    async with engine.connect() as conn:
        settings_str = await conn.scalar(
            text("SELECT chat_settings from premium_chats WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )
        
    settings = {}
    if settings_str:
        for el in settings_str.split(' - '):
            if ':' in el:
                key, val = el.split(':', 1)
                if val.startswith('bool='):
                    settings[key] = bool(int(val.split('=')[1]))
                elif val.isdigit():
                    settings[key] = int(val)
                else:
                    settings[key] = val
    return settings


async def update_prem_char(char_type, chat_id, char_list):
    async with engine.begin() as conn:
        await conn.execute(
            text(f"UPDATE premium_chats SET {char_type} = :char_list WHERE chat_id = :chat_id"),
            {'chat_id': chat_id, 'char_list': char_list}
        )


async def update_prem_cataclysm(chat_id, char_list):
    async with engine.begin() as conn:
        cataclysms = await conn.scalar(
            text("SELECT cataclysm FROM premium_chats WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )
        cataclysm_text = f"{cataclysms}_{char_list}" if cataclysms and cataclysms != 'default' else char_list
        await conn.execute(
            text("UPDATE premium_chats SET cataclysm = :char_list WHERE chat_id = :chat_id"),
            {'chat_id': chat_id, 'char_list': cataclysm_text}
        )
    return cataclysm_text


async def update_cataclysm(chat_id, cataclysm_text):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE premium_chats SET cataclysm = :char_list WHERE chat_id = :chat_id"),
            {'chat_id': chat_id, 'char_list': cataclysm_text}
        )


async def update_bonus():
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users1 SET use_bonus = 0"))


async def reward_money(reward: int, user_id: int):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET balance = balance + :reward WHERE user_id = :user_id"),
            {'reward': reward, 'user_id': user_id}
        )


async def premium(chat_id: int):
    async with engine.begin() as conn:
        premium_status = await conn.scalar(
            text("SELECT chat_id FROM premium_chats WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )
        status = await conn.scalar(
            text("SELECT chat_status FROM chats WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )
        
        await conn.execute(
            text("UPDATE chats SET chat_status = 'premium' WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )
        
        if not premium_status:
            await conn.execute(
                text("INSERT INTO premium_chats(chat_id) VALUES(:chat_id)"),
                {'chat_id': chat_id}
            )
        return status


async def not_premium(chat_id: int):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE chats SET chat_status = 'default' WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )


async def state_bonus(user_id: int):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT use_bonus FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def use_bonus(user_id: int):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET use_bonus = 1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def get_user_id():
    async with engine.connect() as conn:
        chats = (await conn.execute(text("SELECT chat_id from chats"))).fetchall()
        users = (await conn.execute(text("SELECT user_id from users1"))).fetchall()
    return chats + users


async def get_invite_number():
    async with engine.connect() as conn:
        return await conn.scalar(text("SELECT invite_number from admin_db"))


async def activate_premium_chat(chat_id: int, duration_days: int = 30):
    """
    Активирует премиум для чата на указанное количество дней (по умолчанию 30).
    Создает дефолтную запись, если ее нет.
    """
    async with engine.begin() as conn:
        expire_time = int(time.time()) + (duration_days * 24 * 3600)
        
        await conn.execute(
            text("UPDATE chats SET chat_status = 'premium' WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )
        
        res = await conn.scalar(
            text("SELECT chat_settings FROM premium_chats WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )
        
        if res is None:
            await conn.execute(
                text("""
                    INSERT INTO premium_chats 
                    (chat_id, chat_settings, cataclysm, profession, gender, fact, hobbies, 
                     baggage, health, phobia, addiction, persona, bunker_rooms, supplies, location_bunker) 
                    VALUES 
                    (:chat_id, :settings, 'default', 'default', 'default', 'default', 'default', 
                     'default', 'default', 'default', 'default', 'default', 'default', 'default', 'default')
                """), 
                {'chat_id': chat_id, 'settings': f'expire_date:{expire_time}'}
            )
        else:
            settings_list = res.split(' - ') if res else []
            new_settings = [s for s in settings_list if not s.startswith('expire_date:')]
            new_settings.append(f'expire_date:{expire_time}')
            await conn.execute(
                text("UPDATE premium_chats SET chat_settings = :settings WHERE chat_id = :chat_id"),
                {'settings': ' - '.join(new_settings), 'chat_id': chat_id}
            )


async def check_premium_expiration(chat_id: int) -> bool:
    """
    Проверяет, не истек ли срок премиума.
    Если истек - возвращает чат к базовому статусу.
    """
    async with engine.begin() as conn:
        res = await conn.scalar(text("SELECT chat_settings FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': chat_id})
        if res:
            for s in res.split(' - '):
                if s.startswith('expire_date:'):
                    expire_time = int(s.split(':')[1])
                    if time.time() > expire_time:
                        await conn.execute(text("UPDATE chats SET chat_status = 'basic' WHERE chat_id = :chat_id"), {'chat_id': chat_id})
                        return False
                    return True
    return True