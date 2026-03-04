from APP.Database.models import engine
from sqlalchemy import text
import random
import math

# === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ===
CHAR_INFO_RU = {
    'fact': '✳ Доп. информация',
    'profession': '💼 Профессия',
    'gender': '👤 Био. информация',
    'hobbies': '🧩 Хобби',
    'baggage': '🎒 Багаж',
    'phobia': '🕷 Фобия',
    'addiction': '💊 Зависимость',
    'persona': '😎 Черта характера',
    'bunker_rooms': '🏠 Комнаты бункера',
    'supplies': '🧳 Склад бункера',
    'location_bunker': '🏞 Локация, где находится бункер',
    'health': '🫀 Здоровье'
}

STAGE_LIST = [
    '(Стажёр)', '(Стаж: 1 год)', '(Стаж: 2 года)', '(Стаж: 3 года)', '(Стаж: 4 года)', '(Стаж: 5 лет)',
    '(Стаж: 6 лет)', '(Стаж: 7 лет)', '(Стаж: 8 лет)', '(Стаж: 9 лет)', '(Стаж: 10 лет)',
    '(Стаж: 11 лет)', '(Стаж: 12 лет)', '(Стаж: 13 лет)', '(Стаж: 14 лет)', '(Стаж: 15 лет)',
    '(Стаж: 16 лет)', '(Стаж: 17 лет)', '(Стаж: 18 лет)', '(Стаж: 19 лет)', '(Стаж: 20 лет)',
    '(Стаж: 21 год)', '(Стаж: 22 года)', '(Стаж: 23 года)', '(Стаж: 24 года)', '(Стаж: 25 лет)',
    '(Стаж: 26 лет)', '(Стаж: 27 лет)', '(Стаж: 28 лет)', '(Стаж: 29 лет)', '(Стаж: 30 лет)',
    '(Стаж: 31 год)', '(Стаж: 32 года)', '(Стаж: 33 года)', '(Стаж: 34 года)', '(Стаж: 35 лет)',
    '(Стаж: 36 лет)', '(Стаж: 37 лет)', '(Стаж: 38 лет)', '(Стаж: 39 лет)', '(Стаж: 40 лет)'
]
# ============================


async def rus_name(char, settings=None):
    name = CHAR_INFO_RU.get(char, '🫀 Здоровье')
    is_active = getattr(settings, char, 1) if settings and hasattr(settings, char) else 1
    return [name, is_active]


async def stage(age):
    if 18 < age < 30:
        return random.choice(STAGE_LIST[:age - 18])
    elif age < 19:
        return random.choice(STAGE_LIST[:3])
    elif 29 < age < 45:
        return random.choice(STAGE_LIST[5:age - 18])
    elif 44 < age < 57:
        return random.choice(STAGE_LIST[10:age - 18])
    else:
        return random.choice(STAGE_LIST[15:])


async def get_user_info(user_id):
    async with engine.connect() as conn:
        user = await conn.execute(
            text('SELECT room_id, user_emoji, name, user_id FROM users1 WHERE user_id = :user_id'), 
            {'user_id': user_id}
        )
    return user.fetchone()


async def get_player_by_id(user_id):
    async with engine.connect() as conn:
        info_player = await conn.execute(
            text("SELECT profession, gender, health, hobbies, baggage, fact, cataclysm, phobia, addiction, persona "
                 "FROM players WHERE player_id = :user_id"), 
            {'user_id': user_id}
        )
    return info_player.fetchone()


async def players(room_id, user_id):
    async with engine.connect() as conn:
        user_in_room = await conn.execute(
            text("SELECT user_id, name, user_emoji FROM users1 "
                 "WHERE room_id = :room_id and user_id <> :user_id and in_game = 1"),
            {'room_id': room_id, 'user_id': user_id}
        )
    return user_in_room.fetchall()


async def select_room_cataclysm(user_id):
    async with engine.connect() as conn:
        cataclysm_full = await conn.scalar(
            text("SELECT cataclysm FROM players WHERE player_id = :user_id"), 
            {'user_id': user_id}
        )
        cataclysm_name = cataclysm_full.split("_")[1].capitalize() if cataclysm_full else ""
        desc = await conn.scalar(
            text("SELECT description FROM cataclysm WHERE cataclysm_name = :name"), 
            {'name': cataclysm_name}
        )
    return desc


async def close_rooms():
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET in_game = 0, room_id = NULL, voice_for_player = 0, player_voice = 0, "
                 "open_characteristics = 0, voice_emoji = NULL, user_emoji = NUll, skip_votes = 0, use_pcard = 0"))
        await conn.execute(text("DELETE FROM players"))


async def select_text_event_in_room(room_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT event_text FROM rooms WHERE room_id = :room_id"), 
            {'room_id': room_id}
        )


async def get_player_card(user_id):
    try:
        async with engine.connect() as conn:
            info = await conn.scalar(
                text("SELECT card FROM players WHERE player_id = :user_id"), 
                {'user_id': user_id}
            )
            return info if info is not None else 'open_none'
    except Exception:
        return 'open_none'


async def get_card(name_card):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT description FROM card WHERE name_card = :name_card"), 
            {'name_card': name_card}
        )


async def select_bunker_characteristics(room_id):
    async with engine.connect() as conn:
        info = await conn.execute(
            text("SELECT bunker_rooms, location_bunker, supplies FROM bunkers_in_game WHERE room_id = :room_id"), 
            {'room_id': room_id}
        )
    return info.fetchone()


async def regeneration_characteristics_select(char, room):
    async with engine.connect() as conn:
        settings_value = await rus_name(char, room.prem_settings)
        if settings_value[1]:
            chars = await conn.scalar(
                text(f"SELECT {char} FROM premium_chats WHERE chat_id = :chat_id"), 
                {'chat_id': room.chat_id}
            )
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            result = random.sample(list(chars_dict.items()), k=3)
        else:
            result = (await conn.execute(
                text(f"SELECT id, {char}_name FROM {char} ORDER BY RANDOM() LIMIT 3")
            )).fetchall()
    return result


async def get_money_and_pcard(user_id):
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT balance, use_pcard FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )
    return res.fetchone()


async def update_room_id_group(user_id, room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET room_id = :room_id WHERE user_id = :user_id"),
            {'room_id': room_id, 'user_id': user_id}
        )


async def player_characteristics(number_of_players):
    if number_of_players % 2 != 0:
        man_limit = int((number_of_players - 1) / 2)
        woman_limit = int((number_of_players - 1) / 2 + 1)
    else:
        man_limit = int(number_of_players / 2)
        woman_limit = man_limit
        
    async with engine.connect() as conn:
        data = await conn.execute(
            text("SELECT "
                 "(SELECT GROUP_CONCAT(profession_name, ';') FROM "
                 "(SELECT profession_name FROM profession ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(gender_name, ';') "
                 "FROM (SELECT gender_name FROM (SELECT gender_name FROM gender "
                 "WHERE gender_name LIKE 'Парень%' OR gender_name LIKE 'Мужчина%' OR gender_name LIKE 'Дед%' "
                 "ORDER BY RANDOM() LIMIT :man_limit) AS male_genders UNION ALL "
                 "SELECT gender_name FROM (SELECT gender_name FROM gender "
                 "WHERE gender_name LIKE 'Девушка%' OR gender_name LIKE 'Женщина%' OR gender_name LIKE 'Бабушка%' "
                 "ORDER BY RANDOM() LIMIT :woman_limit) AS female_genders)), "
                 "(SELECT GROUP_CONCAT(health_name, ';') FROM "
                 "(SELECT health_name FROM health ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(hobbies_name, ';') FROM "
                 "(SELECT hobbies_name FROM hobbies ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(baggage_name, ';') FROM "
                 "(SELECT baggage_name FROM baggage ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(fact_name, ';') FROM "
                 "(SELECT fact_name FROM fact ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(phobia_name, ';') FROM "
                 "(SELECT phobia_name FROM phobia ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(addiction_name, ';') FROM "
                 "(SELECT addiction_name FROM addiction ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(persona_name, ';') FROM "
                 "(SELECT persona_name FROM persona ORDER BY RANDOM() LIMIT :limit)), "
                 "(SELECT GROUP_CONCAT(name_card, ';') FROM "
                 "(SELECT name_card FROM card ORDER BY RANDOM() LIMIT :limit));"),
            {'limit': number_of_players, 'man_limit': man_limit, 'woman_limit': woman_limit})
            
        a = ['profession', 'gender', 'health', 'hobbies', 'baggage',
             'fact', 'phobia', 'addiction', 'persona', 'card']
        
        char_dict = {a[i]: [n for n in x.split(';')] for i, x in enumerate(data.fetchone())}
        
        child = ['Чайлдфри', 'Бесплодность', 'Хорошая', 'Плохая']
        man = ['Дед', 'Мужчина', 'Парень']
        woman = ['Бабушка', 'Женщина', 'Девушка']
        
        for index in range(len(char_dict['gender'])):
            user_stage = await stage(int(char_dict['gender'][index].split(' ')[1]))
            gender = char_dict['gender'][index].capitalize().split(' ')[0]
            true_if = (gender in man) or (gender in woman)
            user_child = random.choice(child) if true_if else random.choice(['Чайлдфри', 'Хорошая'])
            char_dict['gender'][index] = char_dict['gender'][index] + f'  (плодовитость: {user_child})'
            char_dict['profession'][index] = char_dict['profession'][index] + ' ' + user_stage
            
        cataclysm_data = await conn.execute(text("SELECT cataclysm_name, description FROM cataclysm ORDER BY RANDOM() LIMIT 1"))
        char_dict['cataclysm'] = '+'.join(cataclysm_data.fetchone())
        
        return char_dict


async def bunker_characteristics():
    async with engine.connect() as conn:
        data = await conn.execute(
            text("SELECT "
                 "(SELECT GROUP_CONCAT(location_bunker, ';') "
                 "FROM (SELECT location_bunker FROM bunkers_characteristics ORDER BY RANDOM() LIMIT 1)), "
                 "(SELECT GROUP_CONCAT(supplies, ';') "
                 "FROM (SELECT supplies FROM bunkers_characteristics ORDER BY RANDOM() LIMIT 2)), "
                 "(SELECT GROUP_CONCAT(bunker_rooms, ';') "
                 "FROM (SELECT bunker_rooms FROM bunkers_characteristics  ORDER BY RANDOM() LIMIT 3));"))
                 
        a = ['location', 'supplies', 'rooms']
        return {a[i]: [n for n in x.split(';')] if a[i] != 'location' else [n for n in x.split(';')][0] 
                for i, x in enumerate(data.fetchone())}


async def insert_player_characteristics(player_id, profession, gender, fact, cataclysm, hobbies, baggage,
                                        health, room_id, phobia, addiction, persona, card, emoji):
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO players (player_id, profession, gender, fact, cataclysm, hobbies, "
                 "baggage, health, room_id, phobia, addiction, persona, card) "
                 "VALUES (:player_id, :profession, :gender, :fact, :cataclysm, :hobbies, :baggage, "
                 ":health, :room_id, :phobia, :addiction, :persona, :card);"),
            {
                'player_id': player_id, 
                'profession': f'open_💼 Профессия_profession_{profession}',
                'gender': f'👤 Био информация_gender_{gender}', 
                'fact': f'✳ Доп. информация_fact_{fact}',
                'cataclysm': f'const_{cataclysm}', 
                'hobbies': f'🧩 Хобби_hobbies_{hobbies}',
                'baggage': f'🎒 Багаж_baggage_{baggage}', 
                'health': f'🫀 Здоровье_health_{health}',
                'room_id': f'{room_id}', 
                'phobia': f'🕷 Фобия_phobia_{phobia}',
                'addiction': f'💊 Зависимость_addiction_{addiction}',
                'persona': f'😎 Черта характера_persona_{persona}',
                'card': f'🃏 Карта действия_card_{card}'
            }
        )
        await conn.execute(
            text("UPDATE users1 SET user_emoji = :emoji WHERE user_id = :user_id"),
            {'emoji': emoji, 'user_id': player_id}
        )
        await conn.execute(
            text("UPDATE users1 SET in_game = 1 WHERE user_id = :player_id"), 
            {'player_id': player_id}
        )


async def select_open_characteristics_in_room(room_id):
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT open_characteristics FROM users1 WHERE room_id = :room_id and in_game = 1"),
            {'room_id': room_id}
        )
        return list(res.scalars().all())


async def select_not_open_characteristics_in_room(room_id):
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT user_id FROM users1 WHERE room_id = :room_id and in_game = 1 and open_characteristics = 0"),
            {'room_id': room_id}
        )
        return list(res.scalars().all())


async def update_characteristics(user_id, characteristics_name):
    async with engine.begin() as conn:
        old_val = await conn.scalar(
            text(f"SELECT {characteristics_name} FROM players WHERE player_id = :user_id"),
            {'user_id': user_id}
        )
        new_text = 'open_' + old_val
        
        await conn.execute(
            text(f"UPDATE players SET {characteristics_name} = :new_text WHERE player_id = :user_id"),
            {'new_text': new_text, 'user_id': user_id}
        )
        await conn.execute(
            text("UPDATE users1 SET open_characteristics = 1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def get_active_players_emoji(room_id):
    async with engine.connect() as conn:
        users = await conn.execute(
            text("SELECT name, user_emoji, voice_emoji, user_id, voice_for_player "
                 "FROM users1 WHERE room_id = :room_id and in_game = 1"),
            {'room_id': room_id}
        )
    return users.fetchall()


async def get_skip_votes_players(room_id):
    async with engine.connect() as conn:
        users = await conn.execute(
            text("SELECT user_emoji FROM users1 WHERE room_id = :room_id and in_game = 1 and skip_votes = 1"),
            {'room_id': room_id}
        )
        emojis = list(users.scalars().all())
        
    result_text = ', '.join([f"[{e}]" for e in emojis])
    return [result_text if result_text else 0, len(emojis)]


async def get_active_user_in_room(room_id):
    async with engine.connect() as conn:
        user_in_room = await conn.execute(
            text("SELECT user_id, name FROM users1 WHERE room_id = :room_id and in_game = 1"),
            {'room_id': room_id}
        )
    return user_in_room.fetchall()


async def get_player_out(room_id, number):
    async with engine.connect() as conn:
        info_player = await conn.execute(
            text("SELECT user_id, name, user_emoji FROM users1 WHERE room_id = :room_id and "
                 "voice_for_player = :number and in_game = 1"),
            {'number': number, 'room_id': room_id}
        )
    return info_player.fetchall()


async def get_skip_votes(room_id):
    async with engine.connect() as conn:
        # Моментальный подсчет через SQL
        return await conn.scalar(
            text("SELECT COUNT(*) FROM users1 WHERE room_id = :room_id and in_game = 1 and skip_votes = 1"),
            {'room_id': room_id}
        )


async def get_voice_for_player_info(room_id):
    async with engine.connect() as conn:
        info_player = await conn.execute(
            text("SELECT voice_for_player, name FROM users1 WHERE room_id = :room_id and in_game = 1"),
            {'room_id': room_id}
        )
    return info_player.fetchall()


async def get_user_card(user_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT card FROM players WHERE player_id = :user_id"), 
            {'user_id': user_id}
        )


async def player_out(user_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET in_game = 0, defeat = defeat + 1, balance = balance + 10,"
                 "user_statistics = ROUND(100.0 * victory / (victory + defeat + 1), 2) WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def new_votes(room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET player_voice = 0, voice_for_player = 0, voice_emoji = NULL WHERE room_id = :room_id"), 
            {'room_id': room_id}
        )


async def new_round(room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET player_voice = 0, skip_votes = 0, voice_for_player = 0, open_characteristics = 0, "
                 "voice_emoji = NULL WHERE room_id = :room_id"),
            {'room_id': room_id}
        )


async def player_win(user_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET victory = victory + 1, balance = balance + 30, user_statistics = "
                 "ROUND(100.0 * (victory + 1) / (victory + defeat + 1), 2) WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def get_chat_status(chat_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT chat_status FROM chats WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )


async def close_room_db(room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET in_game = 0, room_id = NULL, voice_for_player = 0, player_voice = 0, "
                 "open_characteristics = 0, voice_emoji = NULL, user_emoji = NUll, skip_votes = 0, use_pcard = 0 "
                 "WHERE room_id = :room_id"),
            {'room_id': room_id}
        )
        await conn.execute(text("DELETE FROM players WHERE room_id = :room_id"), {'room_id': room_id})


async def chat_game(chat_id, chat_name, chat_member):
    async with engine.begin() as conn:
        res = await conn.scalar(
            text("SELECT chat_id FROM chats WHERE chat_id = :chat_id"), 
            {'chat_id': chat_id}
        )
        if res is not None:
            await conn.execute(
                text("UPDATE chats SET chat_name = :chat_name, chat_game = chat_game + 1, chat_member = :chat_member "
                     "WHERE chat_id = :chat_id"),
                {'chat_id': chat_id, 'chat_name': chat_name, 'chat_member': chat_member}
            )
        else:
            await conn.execute(
                text("INSERT INTO chats (chat_id, chat_name, chat_active, chat_game, chat_member) "
                     "VALUES(:chat_id, :chat_name, 1, 1, :chat_member)"),
                {'chat_id': chat_id, 'chat_name': chat_name, 'chat_member': chat_member}
            )


async def select_char_player_card(char, card_user_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text(f"SELECT {char} FROM players WHERE player_id = :user_id"),
            {'user_id': card_user_id}
        )


async def get_name(user_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT name FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def change_characteristics(char, user_id, card_user_id, result):
    async with engine.begin() as conn:
        card = await conn.scalar(text(f"SELECT {char} FROM players WHERE player_id = :user_id"), {'user_id': card_user_id})
        player = await conn.scalar(text(f"SELECT {char} FROM players WHERE player_id = :user_id"), {'user_id': user_id})
        
        c_parts = card.split('_')
        p_parts = player.split('_')
        
        new_card_char = f"{result}_{c_parts[-2]}_{c_parts[-1]}"
        if player[:4] == 'open': new_card_char = "open_" + new_card_char
            
        new_user_char = f"{result}_{p_parts[-2]}_{p_parts[-1]}"
        if card[:4] == 'open': new_user_char = "open_" + new_user_char
            
        await conn.execute(
            text(f"UPDATE players SET {char} = :new_char WHERE player_id = :user_id"),
            {'user_id': user_id, 'new_char': new_card_char}
        )
        await conn.execute(
            text(f"UPDATE players SET {char} = :new_char WHERE player_id = :user_id"),
            {'user_id': card_user_id, 'new_char': new_user_char}
        )
    return [card, player]


async def delete_baggage(room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE players SET baggage = 'open_🎒 Багаж_baggage_Отсутствует' "
                 "WHERE room_id = :room_id and baggage LIKE 'open_%'"),
            {'room_id': room_id}
        )
        await conn.execute(
            text("UPDATE players SET baggage = '🎒 Багаж_baggage_Отсутствует' "
                 "WHERE room_id = :room_id and baggage NOT LIKE 'open_%'"),
            {'room_id': room_id}
        )


async def select_random_event(event_in_room):
    # Оптимизированная логика запроса NOT IN
    ignored_ids = [str(i) for i in event_in_room]
    sql_text = f"WHERE events_id NOT IN ({','.join(ignored_ids)}) " if ignored_ids else ""
    
    async with engine.connect() as conn:
        return (await conn.execute(
            text(f"SELECT event_name, events_id, code_name FROM events {sql_text} ORDER BY RANDOM() LIMIT 1")
        )).fetchone()


async def healer_characteristics(char, user_id, new_char, result):
    async with engine.begin() as conn:
        old_char = await conn.scalar(
            text(f"SELECT {char} FROM players WHERE player_id = :user_id"),
            {'user_id': user_id}
        )
        old_parts = old_char.split('_')
        new_user_char = f"{result}_{old_parts[-2]}_{new_char}"
        if old_char[:4] == 'open':
            new_user_char = "open_" + new_user_char
            
        await conn.execute(
            text(f"UPDATE players SET {char} = :new_char WHERE player_id = :user_id"),
            {'new_char': new_user_char, 'user_id': user_id}
        )


async def update_health(user_id, room_id):
    async with engine.begin() as conn:
        users = (await conn.execute(
            text("SELECT user_id, name, user_emoji FROM users1 WHERE room_id = :room_id and in_game = 1 "
                 "ORDER BY RANDOM() LIMIT 1"),
            {'room_id': room_id}
        )).fetchone()
        
        card = await conn.scalar(text("SELECT health FROM players WHERE player_id = :uid"), {'uid': users[0]})
        player = await conn.scalar(text("SELECT health FROM players WHERE player_id = :uid"), {'uid': user_id})
        
        c_parts = card.split('_')
        p_parts = player.split('_')
        
        new_card_char = f"🫀 Здоровье_{c_parts[-2]}_{c_parts[-1]}"
        if player[:4] == 'open': new_card_char = "open_" + new_card_char
            
        new_user_char = f"🫀 Здоровье_{p_parts[-2]}_{p_parts[-1]}"
        if card[:4] == 'open': new_user_char = "open_" + new_user_char
            
        await conn.execute(
            text("UPDATE players SET health = :new_char WHERE player_id = :user_id"),
            {'new_char': new_card_char, 'user_id': user_id}
        )
        await conn.execute(
            text("UPDATE players SET health = :new_char WHERE player_id = :user_id"),
            {'new_char': new_user_char, 'user_id': users[0]}
        )
    return [c_parts[-1], p_parts[-1], users]


async def get_msg_start(user_id):
    async with engine.connect() as conn:
        return await conn.scalar(
            text("SELECT start_message_delete FROM users1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def delete_baggage_card(room_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE players SET baggage = 'open_🎒 Багаж_baggage_Отсутствует' "
                 "WHERE room_id = :room_id and baggage LIKE 'open_%'"),
            {'room_id': room_id}
        )


async def revers_profession(room_id):
    async with engine.begin() as conn:
        result = (await conn.execute(
            text("SELECT p.player_id, p.profession FROM players p INNER JOIN users1 u " 
                 "ON p.player_id = u.user_id WHERE u.room_id = :room_id AND u.in_game = 1;"),
            {'room_id': room_id})
        ).fetchall()
        
        profession = [x[1] for x in result]
        profession.reverse()
        
        if len(profession) % 2 != 0:
            index = math.ceil(len(profession) / 2)
            profession[1], profession[index] = profession[index], profession[1]
            
        for i, user in enumerate(result):
            await conn.execute(
                text("UPDATE players SET profession = :profession WHERE player_id = :user_id"),
                {'profession': profession[i], 'user_id': user[0]}
            )


async def pcard1(user_id, room):
    async with engine.begin() as conn:
        chat_status = await get_chat_status(room.chat_id)
        res = (await conn.execute(
            text("SELECT gender, profession, health, hobbies, baggage, fact, phobia, addiction, persona "
                 "FROM players WHERE player_id = :uid"), {'uid': user_id}
        )).fetchone()
        
        player_info = [x for x in res if not x.startswith('open_')]
        select_list = []
        
        if chat_status == 'premium':
            chars = (await conn.execute(
                text("SELECT gender, profession, health, hobbies, baggage, fact, phobia, addiction, persona FROM "
                     "premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id}
            )).fetchone()
            
            char_names = ['gender', 'profession', 'health', 'hobbies', 'baggage', 'fact', 'phobia', 'addiction', 'persona']
            chars_value = dict(zip(char_names, chars))
            
            for x in player_info:
                p_parts = x.split('_')
                char_type = p_parts[1]
                settings_value = await rus_name(char_type, room.prem_settings)
                
                if chars_value.get(char_type) != 'default' and settings_value[1]:
                    char = random.choice(chars_value[char_type].split('_'))
                    select_list.append([char, p_parts[0], char_type])
                elif char_type == 'profession' and not (await rus_name('gender', room.prem_settings))[1]:
                    user_char = await conn.scalar(text("SELECT profession_name FROM profession ORDER BY RANDOM() LIMIT 1"))
                    user_profession = user_char + ' ' + await stage(int(select_list[0][0].split(' ')[1]))
                    select_list.append([user_profession, p_parts[0], char_type])
                elif char_type == 'gender':
                    user_char = await conn.scalar(text("SELECT gender_name FROM gender ORDER BY RANDOM() LIMIT 1"))
                    user_child = random.choice(['Чайлдфри', 'Бесплодность', 'Хорошая', 'Плохая'])
                    user_gender = user_char + f' (плодовитость: {user_child})'
                    select_list.append([user_gender, p_parts[0], char_type])
                else:
                    char = await conn.scalar(text(f"SELECT {char_type}_name FROM {char_type} ORDER BY RANDOM() LIMIT 1"))
                    select_list.append([char, p_parts[0], char_type])
        else:
            for x in player_info:
                p_parts = x.split('_')
                char_type = p_parts[1]
                char = await conn.scalar(text(f"SELECT {char_type}_name FROM {char_type} ORDER BY RANDOM() LIMIT 1"))
                select_list.append([char, p_parts[0], char_type])
                
        # Исправлена логика SQL апдейта для безопасного формирования
        update_parts = []
        for x in select_list:
            # x = [значение, префикс, имя_колонки]
            update_parts.append(f"{x[2]} = '{x[1]}_{x[2]}_{x[0]}'")
            
        if update_parts:
            text_sql = ", ".join(update_parts)
            await conn.execute(
                text(f"UPDATE players SET {text_sql} WHERE player_id = :user_id"),
                {'user_id': user_id}
            )
    return select_list


async def use_pcard(user_id, balance):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET use_pcard = 1, balance = balance - :balance WHERE user_id = :user_id"),
            {'user_id': user_id, 'balance': balance}
        )


async def use_card(user_id):
    async with engine.begin() as conn:
        old_val = await conn.scalar(text("SELECT card FROM players WHERE player_id = :user_id"), {'user_id': user_id})
        new_text = 'open_' + old_val
        await conn.execute(
            text("UPDATE players SET card = :new_text WHERE player_id = :user_id"),
            {'new_text': new_text, 'user_id': user_id}
        )


async def regeneration_characteristics(char_id, char, user_id, char_name, room):
    async with engine.begin() as conn:
        if (await rus_name(char, room.prem_settings))[1]:
            chars = await conn.scalar(text(f"SELECT {char} FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            result = chars.split('_')[int(char_id)]
        else:
            result = await conn.scalar(text(f"SELECT {char}_name FROM {char} WHERE id = :char_id"), {'char_id': char_id})
            
        player_char = await conn.scalar(text(f"SELECT {char} FROM players WHERE player_id = :user_id"), {'user_id': user_id})
        
        new_char = f"{char_name}_{char}_{result.capitalize()}"
        if player_char[:4] == 'open':
            new_char = "open_" + new_char
            
        await conn.execute(
            text(f"UPDATE players SET {char} = :new_char WHERE player_id = :user_id"),
            {'user_id': user_id, 'new_char': new_char}
        )
    return result


async def voice_for_player(user_id, emoji, user_voice_id):
    async with engine.begin() as conn:
        x = await conn.scalar(text("SELECT voice_emoji FROM users1 WHERE user_id = :uid"), {'uid': user_id})
        # Безопасное формирование строки
        new_emoji = f"{x}, [{emoji}]" if x else f"[{emoji}]"
        
        await conn.execute(
            text("UPDATE users1 SET voice_for_player = voice_for_player + 1, voice_emoji = :new_emoji WHERE user_id = :user_id"),
            {'user_id': user_id, 'new_emoji': new_emoji}
        )
        await conn.execute(
            text("UPDATE users1 SET player_voice = 1 WHERE user_id = :user_id"),
            {'user_id': user_voice_id}
        )


async def player_skip_voice(user_id):
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users1 SET player_voice = 1, skip_votes = 1 WHERE user_id = :user_id"),
            {'user_id': user_id}
        )


async def select_votes_players(room_id):
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT player_voice FROM users1 WHERE room_id = :room_id and in_game = 1"), 
            {'room_id': room_id}
        )
        return list(res.scalars().all())


async def select_char_by_name(user_id, name_char):
    async with engine.connect() as conn:
        return await conn.scalar(
            text(f"SELECT {name_char} FROM players WHERE player_id = :user_id"),
            {'user_id': user_id}
        )


async def select_premium_char(chat_id, settings, players_count):
    char_dict = {}
    async with engine.connect() as conn:
        chars = (await conn.execute(
            text("SELECT gender, profession, health, baggage, fact, hobbies, phobia, addiction, persona FROM "
                 "premium_chats WHERE chat_id = :chat_id"), {'chat_id': chat_id})).fetchone()
                 
        char_names = ['gender', 'profession', 'health', 'baggage', 'fact', 'hobbies', 'phobia', 'addiction', 'persona']
        
        for i, char in enumerate(chars):
            char_type = char_names[i]
            settings_value = await rus_name(char_type, settings)
            
            if char != 'default' and settings_value[1]:
                char_dict[char_type] = random.sample(char.split('_'), k=players_count)
            elif char_type == 'profession' and not (await rus_name('gender', settings))[1]:
                user_char = list((await conn.execute(
                    text("SELECT profession_name FROM profession ORDER BY RANDOM() LIMIT :limit"),
                    {'limit': players_count})).scalars().all())
                for index, x in enumerate(user_char):
                    user_char[index] = x + ' ' + await stage(int(char_dict['gender'][index].split(' ')[1]))
                char_dict[char_type] = user_char
            elif char_type == 'gender':
                user_char = list((await conn.execute(
                    text("SELECT gender_name FROM gender ORDER BY RANDOM() LIMIT :limit"),
                    {'limit': players_count})).scalars().all())
                
                child = ['Чайлдфри', 'Бесплодность', 'Хорошая', 'Плохая']
                man = ['Дед', 'Мужчина', 'Парень']
                woman = ['Бабушка', 'Женщина', 'Девушка']
                
                for index, x in enumerate(user_char):
                    gender = x.capitalize().split(' ')[0]
                    true_if = (gender in man) or (gender in woman)
                    user_child = random.choice(child) if true_if else random.choice(['Чайлдфри', 'Хорошая'])
                    user_char[index] = f"{user_char[index]} (плодовитость: {user_child})"
                char_dict[char_type] = user_char
            else:
                char_dict[char_type] = list((await conn.execute(
                    text(f"SELECT {char_type}_name FROM {char_type} ORDER BY RANDOM() LIMIT :limit"),
                    {'limit': players_count})).scalars().all())
                    
        if settings.cataclysm:
            cataclysm_str = await conn.scalar(
                text("SELECT cataclysm FROM premium_chats WHERE chat_id = :chat_id"),
                {'chat_id': chat_id}
            )
            char_dict['cataclysm'] = random.choice(cataclysm_str.split('_'))
        else:
            cataclysm_data = await conn.execute(text("SELECT cataclysm_name, description FROM cataclysm ORDER BY RANDOM() LIMIT 1"))
            char_dict['cataclysm'] = '+'.join(cataclysm_data.fetchone())
            
        char_dict['card'] = list((await conn.execute(
            text("SELECT name_card FROM card ORDER BY RANDOM() LIMIT :limit"),
            {'limit': players_count})).scalars().all())
            
    return char_dict


async def select_premium_bunker(chat_id, settings):
    bunker_dict = {}
    prem = {'location_bunker': settings.location_bunker, 'bunker_rooms': settings.bunker_rooms, 'supplies': settings.supplies}
    
    query_cols = [k for k, v in prem.items() if v]
    def_cols = [k for k, v in prem.items() if not v]
    
    async with engine.connect() as conn:
        if query_cols:
            query_text = ", ".join(query_cols)
            chars = (await conn.execute(
                text(f"SELECT {query_text} FROM premium_chats WHERE chat_id = :chat_id"), 
                {'chat_id': chat_id})
            ).fetchone()
            
            for i, char in enumerate(chars):
                col_name = query_cols[i]
                limit = 1 if col_name == 'location_bunker' else (2 if col_name == 'supplies' else 3)
                bunker_dict[col_name] = random.sample(char.split('_'), k=limit)
                
        if def_cols:
            for x in def_cols:
                limit = 1 if x == 'location_bunker' else (2 if x == 'supplies' else 3)
                bunker_dict[x] = list((await conn.execute(
                    text(f"SELECT {x} FROM bunkers_characteristics ORDER BY RANDOM() LIMIT :limit"),
                    {'limit': limit}
                )).scalars().all())
                
    bunker_dict['location'] = bunker_dict.pop('location_bunker')
    bunker_dict['rooms'] = bunker_dict.pop('bunker_rooms')
    return bunker_dict


async def regeneration_gender_select(room, state):
    async with engine.connect() as conn:
        if room.prem_settings.gender:
            chars = await conn.scalar(
                text("SELECT gender FROM premium_chats WHERE chat_id = :chat_id"), 
                {'chat_id': room.chat_id}
            )
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            result = random.sample(list(chars_dict.items()), k=3)
        else:
            res = (await conn.execute(text("SELECT gender_name, id FROM gender ORDER BY RANDOM() LIMIT 3"))).fetchall()
            child_dict = {}
            result = []
            for x in res:
                child = random.choice(['Чайлдфри', 'Бесплодность', 'Хорошая', 'Плохая'])
                child_dict[x[1]] = child
                result.append([x[1], f"{x[0]} (плодовитость: {child})"])
            await state.update_data(gender_child=child_dict)
    return result


async def regeneration_gender(char_id, char_name, state, room, user_id):
    async with engine.begin() as conn:
        if room.prem_settings.gender:
            chars = await conn.scalar(
                text("SELECT gender FROM premium_chats WHERE chat_id = :chat_id"), 
                {'chat_id': room.chat_id}
            )
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            result = chars_dict[int(char_id)]
            
            player_char = await conn.scalar(text("SELECT gender FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            new_char = f"{char_name}_gender_{result}"
            if player_char[:4] == 'open':
                new_char = "open_" + new_char
                
            await conn.execute(
                text("UPDATE players SET gender = :new_char WHERE player_id = :user_id"),
                {'user_id': user_id, 'new_char': new_char}
            )
        else:
            data = await state.get_data()
            child_text = data['gender_child'][int(char_id)]
            child = f" (плодовитость: {child_text})"
            
            result = await conn.scalar(text("SELECT gender_name FROM gender WHERE id = :char_id"), {'char_id': char_id})
            player_char = await conn.scalar(text("SELECT gender FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            
            new_char = f"{char_name}_gender_{result.capitalize()}{child}"
            if player_char[:4] == 'open':
                new_char = "open_" + new_char
                
            await conn.execute(
                text("UPDATE players SET gender = :new_char WHERE player_id = :user_id"),
                {'user_id': user_id, 'new_char': new_char}
            )
            
            new_data = {k: v for k, v in data.items() if k != 'gender_child'}
            await state.set_data(new_data)
            result = result + child
            
    return result


async def regeneration_profession_select(room, state, user_id):
    async with engine.connect() as conn:
        if room.prem_settings.profession and room.prem_settings.gender:
            chars = await conn.scalar(text("SELECT profession FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            result = random.sample(list(chars_dict.items()), k=3)
        elif room.prem_settings.profession and not room.prem_settings.gender:
            chars = await conn.scalar(text("SELECT profession FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            user_chars = random.sample(list(chars_dict.items()), k=3)
            
            gender_str = await conn.scalar(text("SELECT gender FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            user_age = int(gender_str.split('_')[-1].split(' ')[1])
            
            child_dict = {}
            result = []
            for x in user_chars:
                stage_user = await stage(user_age)
                child_dict[x[0]] = stage_user
                result.append([x[0], f"{x[1]} {stage_user}"])
            await state.update_data(stage_user=child_dict)
        elif not room.prem_settings.profession and room.prem_settings.gender:
            result = (await conn.execute(text("SELECT id, profession_name FROM profession ORDER BY RANDOM() LIMIT 3"))).fetchall()
        else:
            res = (await conn.execute(text("SELECT profession_name, id FROM profession ORDER BY RANDOM() LIMIT 3"))).fetchall()
            gender_str = await conn.scalar(text("SELECT gender FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            user_age = int(gender_str.split('_')[-1].split(' ')[1])
            
            child_dict = {}
            result = []
            for x in res:
                stage_user = await stage(user_age)
                child_dict[x[1]] = stage_user
                result.append([x[1], f"{x[0]} {stage_user}"])
            await state.update_data(stage_user=child_dict)
    return result


async def regeneration_profession(char_id, char_name, state, room, user_id):
    async with engine.begin() as conn:
        if room.prem_settings.profession and room.prem_settings.gender:
            chars = await conn.scalar(text("SELECT profession FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            result = chars_dict[int(char_id)]
            
            player_char = await conn.scalar(text("SELECT profession FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            new_char = f"{char_name}_profession_{result}"
            if player_char[:4] == 'open': new_char = "open_" + new_char
                
            await conn.execute(text("UPDATE players SET profession = :new_char WHERE player_id = :user_id"), {'user_id': user_id, 'new_char': new_char})
            
        elif room.prem_settings.profession and not room.prem_settings.gender:
            chars = await conn.scalar(text("SELECT profession FROM premium_chats WHERE chat_id = :chat_id"), {'chat_id': room.chat_id})
            chars_dict = {i: x for i, x in enumerate(chars.split('_'))}
            
            data = await state.get_data()
            user_stage = f" {data['stage_user'][int(char_id)]}"
            
            player_char = await conn.scalar(text("SELECT profession FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            new_char = f"{char_name}_profession_{chars_dict[int(char_id)]}{user_stage}"
            if player_char[:4] == 'open': new_char = "open_" + new_char
                
            await conn.execute(text("UPDATE players SET profession = :new_char WHERE player_id = :user_id"), {'user_id': user_id, 'new_char': new_char})
            new_data = {k: v for k, v in data.items() if k != 'stage_user'}
            await state.set_data(new_data)
            result = chars_dict[int(char_id)] + user_stage
            
        elif not room.prem_settings.profession and room.prem_settings.gender:
            result = await conn.scalar(text("SELECT profession_name FROM profession WHERE id = :char_id"), {'char_id': char_id})
            player_char = await conn.scalar(text("SELECT profession FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            
            new_char = f"{char_name}_profession_{result.capitalize()}"
            if player_char[:4] == 'open': new_char = "open_" + new_char
                
            await conn.execute(text("UPDATE players SET profession = :new_char WHERE player_id = :user_id"), {'user_id': user_id, 'new_char': new_char})
            
        else:
            data = await state.get_data()
            user_stage = f" {data['stage_user'][int(char_id)]}"
            result = await conn.scalar(text("SELECT profession_name FROM profession WHERE id = :char_id"), {'char_id': char_id})
            player_char = await conn.scalar(text("SELECT profession FROM players WHERE player_id = :user_id"), {'user_id': user_id})
            
            new_char = f"{char_name}_profession_{result.capitalize()}{user_stage}"
            if player_char[:4] == 'open': new_char = "open_" + new_char
                
            await conn.execute(text("UPDATE players SET profession = :new_char WHERE player_id = :user_id"), {'user_id': user_id, 'new_char': new_char})
            new_data = {k: v for k, v in data.items() if k != 'stage_user'}
            await state.set_data(new_data)
            result = result + user_stage
            
    return result