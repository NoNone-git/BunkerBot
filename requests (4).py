import aiosqlite
import datetime
from config import DB_FILE

async def get_admin_stats() -> dict:
    """Получает общую статистику для главной панели администратора."""
    stats = {
        'users_total': 0, 'users_active': 0, 'users_inactive': 0,
        'users_new_today': 0, 'users_blocked_today': 0,
        'chats_total': 0, 'chats_active': 0, 'chats_inactive': 0,
        'chats_new_today': 0, 'chats_blocked_today': 0
    }
    today = datetime.date.today().isoformat()
    
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            # Статистика пользователей (ЛС)
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                stats['users_total'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1") as cursor:
                stats['users_active'] = (await cursor.fetchone())[0]
            stats['users_inactive'] = stats['users_total'] - stats['users_active']
            
            async with db.execute("SELECT COUNT(*) FROM users WHERE date(created_at) = ?", (today,)) as cursor:
                stats['users_new_today'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 0 AND date(updated_at) = ?", (today,)) as cursor:
                stats['users_blocked_today'] = (await cursor.fetchone())[0]
                
            # Статистика чатов (Группы)
            async with db.execute("SELECT COUNT(*) FROM chats") as cursor:
                stats['chats_total'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM chats WHERE is_active = 1") as cursor:
                stats['chats_active'] = (await cursor.fetchone())[0]
            stats['chats_inactive'] = stats['chats_total'] - stats['chats_active']
            
            async with db.execute("SELECT COUNT(*) FROM chats WHERE date(created_at) = ?", (today,)) as cursor:
                stats['chats_new_today'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM chats WHERE is_active = 0 AND date(updated_at) = ?", (today,)) as cursor:
                stats['chats_blocked_today'] = (await cursor.fetchone())[0]
        except Exception:
            pass # Если таблица chats еще не создана, просто вернем нули
            
    return stats

async def get_ad_campaign_stats(campaign_name: str) -> dict:
    """Получает статистику по конкретной рекламной кампании (включая invite и referral)."""
    stats = {'total': 0, 'langs': {}, 'genders': {'male': 0, 'female': 0, 'unknown': 0}}
    
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            async with db.execute("SELECT language_code, first_name FROM ad_stats WHERE campaign_name = ?", (campaign_name,)) as cursor:
                rows = await cursor.fetchall()
                stats['total'] = len(rows)
                
                for lang, first_name in rows:
                    # Подсчет языков
                    lang = lang or 'unknown'
                    stats['langs'][lang] = stats['langs'].get(lang, 0) + 1
                    
                    # Определение пола по окончанию имени (простая эвристика)
                    gender = 'unknown'
                    if first_name:
                        name_lower = first_name.lower().strip()
                        if name_lower.endswith(('а', 'я', 'a', 'ia')):
                            gender = 'female'
                        else:
                            gender = 'male'
                    stats['genders'][gender] += 1
        except Exception:
            pass # Если таблица ad_stats отсутствует
            
    return stats

async def get_all_ids() -> list:
    """Получает список всех ID пользователей и групп."""
    ids = []
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            # Получаем ID всех пользователей
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                ids.extend([row[0] for row in rows])
        except Exception:
            pass
            
        try:
            # Получаем ID всех групп
            async with db.execute("SELECT chat_id FROM chats") as cursor:
                rows = await cursor.fetchall()
                ids.extend([row[0] for row in rows])
        except Exception:
            pass
            
    return ids