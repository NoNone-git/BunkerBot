from APP.Database.models import engine
from sqlalchemy import text


async def set_chat(chat_id, chat_name, chat_member, chat_username):
    # Оптимизированная логика экранирования. Одна строчка вместо медленного цикла for!
    new_name = chat_name.replace("'", "''").replace(":", "::") if chat_name else chat_name
    
    async with engine.begin() as conn:
        res = await conn.scalar(
            text('SELECT chat_id FROM chats WHERE chat_id = :chat_id'),
            {'chat_id': chat_id}
        )
        
        if not res:
            await conn.execute(
                text("INSERT INTO chats (chat_id, chat_name, chat_active, chat_member, chat_username) "
                     "VALUES(:chat_id, :new_name, 1, :chat_member, :chat_username)"),
                {'chat_id': chat_id, 'new_name': new_name, 'chat_member': chat_member, 'chat_username': chat_username}
            )
        else:
            await conn.execute(
                text("UPDATE chats SET chat_active = 1, chat_member = :chat_member, chat_username = :chat_username, "
                     "chat_name = :new_name WHERE chat_id = :chat_id"),
                {'chat_id': chat_id, 'new_name': new_name, 'chat_member': chat_member, 'chat_username': chat_username}
            )


async def get_hello_ad():
    async with engine.connect() as conn:
        # Автоматическая сборка словаря ключей-значений
        res = (await conn.execute(
            text("SELECT ad_date, ad_text, ad_button, ad_id FROM hello_ad WHERE ad_date = 'default'")
        )).mappings().fetchone()
        
        if res:
            # Возвращаем очищенный от None словарь
            return {k: v for k, v in res.items() if v is not None}
        return None


async def get_chat_status(chat_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT chat_status FROM chats WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )


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


async def kicked(user_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET active = 0 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def out_chat(chat_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE chats SET chat_active = 0 WHERE chat_id = :chat_id"),
            {'chat_id': chat_id}
        )


async def invite():
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE admin_db SET invite_number = invite_number + 1"))
        res = await conn.scalar(text("SELECT invite_number FROM admin_db"))
    return res == 1500