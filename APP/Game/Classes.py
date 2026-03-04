from typing import Any
from APP.BaseFunc.settings import Settings, PremiumSettings
from APP.Game.requests import new_votes, player_out, close_room_db
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from APP.Middlewares.decorators import bad_requests_decorate, retry_bad_decorate
from config import rooms, user_state


class Room:
    def __init__(self, chat_id: int, settings: Settings, start_msg_id: int, user_start: int,
                 prem_settings: PremiumSettings):
        self.chat_id: int = chat_id
        self.settings: Settings = settings
        self.prem_settings: PremiumSettings = prem_settings
        self.players: int = 0
        self.round: int = 0
        self.timer: int = 90
        self.state: str = 'start_register'
        self.round_msg: list[int] = []
        self.win: int | None = None
        self.events_text: list[str] = []
        self.events_ids: list[int] = []
        self.user_start_id: int = user_start
        self.extend: str = 'No'
        self.votes_msg_id: int | None = None
        self.start_msg_id: int = start_msg_id
        self.stop_game: list[int] = []
        self.stop_discussion: list[int] = []
        self.next_round: list[int] = []
        self.player_out: list[int] = []
        self.time_votes: int = 0
        self.time_discussion: int = 0
        self.time_two_votes: int = 0
        self.time_open: int = 0
        self.bot_open: int = 0
        # Исправлен синтаксис аннотаций типов
        self.players_dict: dict[int, dict[str, Any]] = {}
        self.bunker: dict[str, list] = {}
        self.pin_msg_ids: list[int] = []
        self.start_msg_pin: int | bool = False
        self.number_votes: int | None = None
        self.skip_votes: int | None = None

    async def set_user(self, user_id: int, name: str):
        self.players_dict[user_id] = {
            'user_id': user_id, 
            'name': name, 
            'emoji': '[0]', 
            'open': 0, 
            'voice': 0,
            'active': 1
        }
        # Ключи: msg_edit, msg_start, user_id, active, name, emoji, open, voice

    async def new_round_update(self):
        for user in self.players_dict.values():
            if user['active'] == 1:
                user['open'] = 0
                user['voice'] = 0
                
        self.time_votes = 0
        self.time_discussion = 0
        self.time_two_votes = 0
        self.time_open = 0
        self.bot_open = 0
        
        # .clear() работает эффективнее пересоздания [] и не нагружает сборщик мусора
        self.stop_discussion.clear()
        self.next_round.clear()
        self.pin_msg_ids.clear()
        self.player_out.clear()
        self.round_msg.clear()
        
        self.number_votes = None
        self.votes_msg_id = None
        self.round += 1

    async def new_votes(self):
        await new_votes(self.chat_id)
        for player in self.players_dict.values():
            player['voice'] = 0

    async def close_room(self, bot: Bot):
        for user in self.players_dict.values():
            for msg in [user.get('msg_start'), user.get('msg_edit')]:
                if msg is not None:
                    await bad_requests_decorate(bot.delete_message)(chat_id=user['user_id'], message_id=msg)
                    
            state: FSMContext = await user_state(user['user_id'], bot.id)
            await state.clear()
            
        if self.start_msg_pin:
            await retry_bad_decorate(bot.unpin_chat_message)(chat_id=self.chat_id, message_id=self.start_msg_pin)
            
        if self.pin_msg_ids:
            for msg in self.pin_msg_ids:
                await retry_bad_decorate(bot.unpin_chat_message)(chat_id=self.chat_id, message_id=msg)
                
        # Безопасное удаление! .pop(key, None) не вызывает KeyError, если комнаты уже нет.
        rooms.pop(self.chat_id, None)
        await close_room_db(self.chat_id)

    async def set_votes_count(self):
        # Быстрый подсчет активных игроков генератором
        players = sum(1 for p in self.players_dict.values() if p.get('active') == 1)
        
        # Защита от TypeError, если self.win всё ещё None
        players_round = players - (self.win or 0)
        number_of_round = 7 - self.round
        
        if players_round > number_of_round and players_round != 2 * number_of_round:
            self.number_votes = 1
        elif players_round == number_of_round:
            self.number_votes = 1
        elif players_round == 2 * number_of_round:
            self.number_votes = 2
        else:
            self.number_votes = 0

    async def out(self, user_id: int, bot: Bot):
        player = self.players_dict.get(user_id)
        if not player:
            return  # Защита от KeyError
            
        state: FSMContext = await user_state(user_id, bot.id)
        await state.clear()
        
        player['active'] = 0
        for msg in [player.get('msg_start'), player.get('msg_edit')]:
            if msg is not None:
                await bad_requests_decorate(bot.delete_message)(chat_id=user_id, message_id=msg)
                
        await player_out(user_id)