import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .system_prompt import SYSTEM_PROMPT

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    openai_api_key: str
    openai_model: str
    system_prompt: str
    history_limit: int
    webhook_url: str | None
    webhook_port: int


def load_settings() -> Settings:
    return Settings(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        system_prompt=SYSTEM_PROMPT,
        history_limit=int(os.environ.get("HISTORY_LIMIT", "10")),
        webhook_url=os.environ.get("WEBHOOK_URL") or None,
        webhook_port=int(os.environ.get("WEBHOOK_PORT", "8080")),
    )
