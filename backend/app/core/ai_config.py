import os


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_deepseek_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")


def get_active_llm_api_key() -> str | None:
    pipeline = (os.getenv("NMM_AI_PIPELINE") or os.getenv("AI_PIPELINE") or "").strip().lower()
    if pipeline in ("openai", "openai_vision", "openai-vision", "oai"):
        return get_openai_api_key()
    if pipeline in ("deepseek", "deepseek_google", "deepseek-google"):
        return get_deepseek_api_key()
    return get_openai_api_key() or get_deepseek_api_key()
