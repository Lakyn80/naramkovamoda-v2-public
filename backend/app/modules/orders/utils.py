from datetime import datetime


def generate_vs() -> str:
    return datetime.now().strftime("%Y%d%m%H%M")
