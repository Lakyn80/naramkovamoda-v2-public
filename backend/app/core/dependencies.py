from .config import Settings, get_settings


def settings() -> Settings:
    return get_settings()
