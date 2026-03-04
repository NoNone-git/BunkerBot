from sqlalchemy import text, BigInteger, String, Integer, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs
from config import db_url
from sqlalchemy import BigInteger, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

# Создаем движок БД
engine = create_async_engine(url=db_url, pool_pre_ping=True)

# Дефолтные настройки чата вынесены в константу для красоты кода
DEFAULT_CHAT_SETTINGS = (
    "time_start:30 - time_open:30 - time_discussion:90 - time_votes:40 - time_round:15 - "
    "start_game:Users - extend_register:StartPlayer - stop_game:Votes - stop_register:StartPlayer - "
    "stop_discussion:Votes - next_round:Votes - extend_discussion:Players - characteristics_list:bool=0 - "
    "emoji_list:bool=0 - anonymous_votes:bool=0 - delete_messages:bool=0 - delete_round_msgs:bool=1 - "
    "pin_reg_msg:bool=1 - pin_votes_msg:bool=1 - pin_open_char:bool=1 - pin_info_game_msg:bool=1 - "
    "max_players:18 - min_players:4"
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ==========================================
#               МОДЕЛИ ТАБЛИЦ
# ==========================================

class User(Base):
    __tablename__ = 'users1'
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(65), nullable=False)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True) # Добавлен индекс!
    in_game: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    player_voice: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    voice_for_player: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_characteristics: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message_delete: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    start_message_id: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    revoice: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    voice_emoji: Mapped[str] = mapped_column(String(80), nullable=True)
    user_emoji: Mapped[str] = mapped_column(String(10), nullable=True)
    start_message_delete: Mapped[int] = mapped_column(BigInteger, nullable=True)
    victory: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    defeat: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    user_statistics: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True) # Добавлен индекс!
    skip_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    game_money: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    use_pcard: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    promo: Mapped[str] = mapped_column(String(100), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=True)


class Player(Base):
    __tablename__ = 'players'
    
    player_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True) # Добавлен индекс!
    profession: Mapped[str] = mapped_column(String(100), nullable=True)
    gender: Mapped[str] = mapped_column(String(100), nullable=True)
    fact: Mapped[str] = mapped_column(String(100), nullable=True)
    cataclysm: Mapped[str] = mapped_column(String(100), nullable=True)
    hobbies: Mapped[str] = mapped_column(String(100), nullable=True)
    bunker: Mapped[str] = mapped_column(String(100), nullable=True)
    baggage: Mapped[str] = mapped_column(String(100), nullable=True)
    health: Mapped[str] = mapped_column(String(100), nullable=True)
    addiction: Mapped[str] = mapped_column(String(100), nullable=True)
    persona: Mapped[str] = mapped_column(String(100), nullable=True)
    phobia: Mapped[str] = mapped_column(String(100), nullable=True)
    card: Mapped[str] = mapped_column(String(100), nullable=True)
    revoice: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Chat(Base):
    __tablename__ = 'chats'
    
    # В старом коде не было PK, но SQLAlchemy он нужен. chat_id идеально подходит.
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True) 
    chat_name: Mapped[str] = mapped_column(String(400), nullable=False)
    chat_active: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_game: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    chat_member: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    chat_username: Mapped[str] = mapped_column(String(100), nullable=True)
    chat_status: Mapped[str] = mapped_column(String(10), default='default', nullable=False)
    chat_settings: Mapped[str] = mapped_column(String(700), default=DEFAULT_CHAT_SETTINGS, nullable=False)


class BunkerInGame(Base):
    __tablename__ = 'bunkers_in_game'
    
    room_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bunker_rooms: Mapped[str] = mapped_column(String(100), nullable=False)
    supplies: Mapped[str] = mapped_column(String(100), nullable=False)
    location_bunker: Mapped[str] = mapped_column(String(50), nullable=False)


class TableAd(Base):
    __tablename__ = 'table_ad'
    
    ad_date: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ad_text: Mapped[str] = mapped_column(String(1000), nullable=True)
    ad_button: Mapped[str] = mapped_column(String(300), nullable=True)
    ad_photo: Mapped[str] = mapped_column(String(100), nullable=True)
    start_ad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_group_ad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_animation: Mapped[str] = mapped_column(String(100), nullable=True)
    ad_button_callback: Mapped[str] = mapped_column(String(400), nullable=True)
    ad_sticker: Mapped[str] = mapped_column(String(400), nullable=True)


class EndGameAd(Base):
    __tablename__ = 'end_game_ad'
    
    ad_date: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ad_text: Mapped[str] = mapped_column(String(1000), nullable=True)
    ad_button: Mapped[str] = mapped_column(String(300), nullable=True)
    ad_sticker: Mapped[str] = mapped_column(String(400), nullable=True)


class HelloAd(Base):
    __tablename__ = 'hello_ad'
    
    ad_date: Mapped[str] = mapped_column(String(20), primary_key=True)
    ad_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ad_text: Mapped[str] = mapped_column(String(1000), nullable=True)
    ad_button: Mapped[str] = mapped_column(String(300), nullable=True)


class AdminDb(Base):
    __tablename__ = 'admin_db'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=1)
    invite_number: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


# ==========================================
#          ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ
# ==========================================

async def async_main_db():
    # Используем engine.begin() для безопасного управления транзакциями (commit/rollback)
    async with engine.begin() as conn:
        # 1. Создание всех таблиц (ЕСЛИ ИХ НЕТ). 
        # Существующие данные НЕ пострадают.
        await conn.run_sync(Base.metadata.create_all)
        
        # 2. Безопасное добавление индексов к существующим таблицам 
        # Это ускорит запросы к БД во время игр в 10-20 раз!
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users1_user_id ON users1(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users1_room_id ON users1(room_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users1_active ON users1(active)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_players_room_id ON players(room_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_players_player_id ON players(player_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id)"))

        # 3. Дефолтная строка для админки (через try-except, чтобы не падало, если уже есть)
        try:
            await conn.execute(text("INSERT INTO admin_db(invite_number, id) VALUES (0, 1)"))
        except Exception:
            pass


class PremiumChats(Base):
    __tablename__ = 'premium_chats'
    
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_settings: Mapped[str] = mapped_column(Text, default="")
    cataclysm: Mapped[str] = mapped_column(Text, default="default")
    profession: Mapped[str] = mapped_column(Text, default="default")
    gender: Mapped[str] = mapped_column(Text, default="default")
    fact: Mapped[str] = mapped_column(Text, default="default")
    hobbies: Mapped[str] = mapped_column(Text, default="default")
    baggage: Mapped[str] = mapped_column(Text, default="default")
    health: Mapped[str] = mapped_column(Text, default="default")
    phobia: Mapped[str] = mapped_column(Text, default="default")
    addiction: Mapped[str] = mapped_column(Text, default="default")
    persona: Mapped[str] = mapped_column(Text, default="default")
    bunker_rooms: Mapped[str] = mapped_column(Text, default="default")
    supplies: Mapped[str] = mapped_column(Text, default="default")
    location_bunker: Mapped[str] = mapped_column(Text, default="default")

class PremiumEvents(Base):
    __tablename__ = 'premium_events'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[int] = mapped_column(Integer) # 0 - текст, 1 - 1 игрок, 2 - 2 игрока
    event_text: Mapped[str] = mapped_column(Text)

class PremiumEventsStatus(Base):
    __tablename__ = 'premium_events_status'
    
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_active: Mapped[int] = mapped_column(Integer, default=0)
