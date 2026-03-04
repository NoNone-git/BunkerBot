from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject, User
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, throttle_time_open: int, throttle_time_other: float,
                 throttle_time_votes: int, throttle_time_end: int, throttle_time_card: int):
        # maxsize увеличен с 1 до 10000, чтобы кэш вмещал всех активных игроков
        self.caches = {
            "open": TTLCache(maxsize=10000, ttl=throttle_time_open),
            "votes": TTLCache(maxsize=10000, ttl=throttle_time_votes),
            "end": TTLCache(maxsize=10000, ttl=throttle_time_end),
            "default": TTLCache(maxsize=10000, ttl=throttle_time_other),
            "card": TTLCache(maxsize=10000, ttl=throttle_time_card)
        }

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        throttling_key = get_flag(data, "throttling_key")
        
        if throttling_key is not None and throttling_key in self.caches:
            # Безопасное получение пользователя из data, так как event может быть любым (Message, CallbackQuery и т.д.)
            user: User | None = data.get("event_from_user")
            
            if user is not None:
                if user.id in self.caches[throttling_key]:
                    return  # Троттлинг сработал, игнорируем апдейт
                else:
                    self.caches[throttling_key][user.id] = None
                    
        return await handler(event, data)


flag_open = {'throttling_key': 'open'}
flag_votes = {'throttling_key': 'votes'}
flag_end = {'throttling_key': 'end'}
flag_card = {'throttling_key': 'card'}
flag_default = {'throttling_key': 'default'}