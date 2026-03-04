import asyncio
from functools import wraps
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest, TelegramForbiddenError

def retry_after_decorate(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except TelegramRetryAfter as _ex:
                # Ждем указанное время и цикл повторяется без создания рекурсии
                await asyncio.sleep(_ex.retry_after)
    return wrapped

def retry_bad_decorate(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except TelegramRetryAfter as _ex:
                await asyncio.sleep(_ex.retry_after)
            except (TelegramBadRequest, TelegramForbiddenError):
                # Объединенный перехват ошибок
                return
    return wrapped

def bad_requests_decorate(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (TelegramBadRequest, TelegramForbiddenError):
            return
    return wrapped
