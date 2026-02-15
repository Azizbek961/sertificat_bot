from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

def _parse_admin_ids(raw: str) -> set[int]:
    raw = (raw or "").strip()
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    db_url: str

def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN .env da yo‘q!")
    return Config(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./quizbot.sqlite3").strip(),
    )