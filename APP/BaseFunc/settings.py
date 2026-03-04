class Settings:
    def __init__(self, settings_dict: dict):
        # Используем .get(), чтобы избежать KeyError, если в старой БД нет новых полей
        self.time_start: int = settings_dict.get('time_start', 30)
        self.time_open: int = settings_dict.get('time_open', 30)
        self.time_discussion: int = settings_dict.get('time_discussion', 90)
        self.time_votes: int = settings_dict.get('time_votes', 40)
        self.time_round: int = settings_dict.get('time_round', 15)
        self.start_game: str = settings_dict.get('start_game', 'Users')
        self.extend_register: str = settings_dict.get('extend_register', 'StartPlayer')
        self.stop_game: str = settings_dict.get('stop_game', 'Votes')
        self.stop_register: str = settings_dict.get('stop_register', 'StartPlayer')
        self.stop_discussion: str = settings_dict.get('stop_discussion', 'Votes')
        self.next_round: str = settings_dict.get('next_round', 'Votes')
        self.extend_discussion: str = settings_dict.get('extend_discussion', 'Players')
        self.characteristics_list: bool = settings_dict.get('characteristics_list', False)
        self.emoji_list: bool = settings_dict.get('emoji_list', False)
        self.anonymous_votes: bool = settings_dict.get('anonymous_votes', False)
        self.delete_messages: bool = settings_dict.get('delete_messages', False)
        self.delete_round_msgs: bool = settings_dict.get('delete_round_msgs', True)
        self.pin_reg_msg: bool = settings_dict.get('pin_reg_msg', True)
        self.pin_votes_msg: bool = settings_dict.get('pin_votes_msg', True)
        self.pin_open_char: bool = settings_dict.get('pin_open_char', True)
        self.pin_info_game_msg: bool = settings_dict.get('pin_info_game_msg', True)
        self.max_players: int = settings_dict.get('max_players', 18)
        self.min_players: int = settings_dict.get('min_players', 4)


class PremiumSettings:
    def __init__(self, premium_settings: dict | bool = False):
        ps = premium_settings if isinstance(premium_settings, dict) else {}
        # Тайпинги исправлены на bool, так как в БД они хранятся как bool=0/1
        self.profession: bool = bool(ps.get('profession', False))
        self.gender: bool = bool(ps.get('gender', False))
        self.health: bool = bool(ps.get('health', False))
        self.hobbies: bool = bool(ps.get('hobbies', False))
        self.baggage: bool = bool(ps.get('baggage', False))
        self.fact: bool = bool(ps.get('fact', False))
        self.phobia: bool = bool(ps.get('phobia', False))
        self.addiction: bool = bool(ps.get('addiction', False))
        self.persona: bool = bool(ps.get('persona', False))
        self.cataclysm: bool = bool(ps.get('cataclysm', False))
        self.events: bool = bool(ps.get('events', False))
        self.location_bunker: bool = bool(ps.get('location_bunker', False))
        self.supplies: bool = bool(ps.get('supplies', False))
        self.bunker_rooms: bool = bool(ps.get('bunker_rooms', False))
        self.ai_format: int = int(ps.get('ai_format', 0))


async def class_settings(settings_text: str):
    settings_dict1 = {}
    if settings_text:
        for el in settings_text.split(' - '):
            if ':' in el:
                key, val = el.split(':', 1)
                if val.isdigit():
                    settings_dict1[key] = int(val)
                elif val.startswith('bool='):
                    settings_dict1[key] = bool(int(val.split('=')[1]))
                else:
                    settings_dict1[key] = str(val)
    return Settings(settings_dict1)


async def bool_text(el: bool):
    return 'bool=1' if el else 'bool=0'


async def settings_dict(settings_class: Settings):
    # vars() мгновенно превращает все атрибуты класса в словарь
    return vars(settings_class).copy()


async def text_settings(settings_class: Settings):
    parts = []
    # Быстрая сборка строки вместо text += '...'
    for k, v in vars(settings_class).items():
        if isinstance(v, bool):
            parts.append(f"{k}:bool={1 if v else 0}")
        else:
            parts.append(f"{k}:{v}")
    return " - ".join(parts)


async def prem_settings_dict(settings_class: PremiumSettings):
    return vars(settings_class).copy()


async def text_prem_settings(settings_class: PremiumSettings):
    parts = []
    for k, v in vars(settings_class).items():
        if isinstance(v, bool):
            parts.append(f"{k}:bool={1 if v else 0}")
        else:
            parts.append(f"{k}:{v}")
    return " - ".join(parts)