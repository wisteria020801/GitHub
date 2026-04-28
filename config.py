import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Dict


env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


@dataclass
class GitHubConfig:
    token: str
    api_base_url: str = "https://api.github.com"
    search_query: str = "stars:>50 created:>7days ago"
    max_results: int = 50
    request_timeout: int = 30


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    channel_id: Optional[str] = None


@dataclass
class WorldNewsBotConfig:
    bot_token: str
    chat_id: str
    channel_id: Optional[str] = None
    enabled: bool = False


@dataclass
class LLMConfig:
    provider: str = "google"
    api_key: str = ""
    model: str = "gemini-2.0-flash"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class DatabaseConfig:
    path: str = "github_radar.db"


@dataclass
class ScoringConfig:
    min_score_to_notify: int = 60
    max_results_per_day: int = 5


@dataclass
class SystemConfig:
    scan_interval_minutes: int = 240
    debug: bool = True


@dataclass
class Config:
    github: GitHubConfig
    telegram: TelegramConfig
    llm: LLMConfig
    database: DatabaseConfig
    scoring: ScoringConfig
    system: SystemConfig
    worldnews_bot: Optional[WorldNewsBotConfig] = None

    @classmethod
    def from_env(cls) -> 'Config':
        github_token = os.getenv('TOKEN_GITHUB', '')
        if not github_token:
            raise ValueError("TOKEN_GITHUB is required in .env file")

        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        if not telegram_token or not telegram_chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required in .env file")

        google_api_key = os.getenv('GOOGLE_API_KEY', '')
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY is required in .env file")

        return cls(
            github=GitHubConfig(
                token=github_token,
            ),
            telegram=TelegramConfig(
                bot_token=telegram_token,
                chat_id=telegram_chat_id,
                channel_id=os.getenv('TELEGRAM_CHATGROUP_ID'),
            ),
            worldnews_bot=WorldNewsBotConfig(
                bot_token=os.getenv('WORLDNEWS_BOT_TOKEN', ''),
                chat_id=os.getenv('WORLDNEWS_CHAT_ID', ''),
                channel_id=os.getenv('WORLDNEWS_CHATGROUP_ID'),
                enabled=bool(os.getenv('WORLDNEWS_BOT_TOKEN', '')),
            ) if os.getenv('WORLDNEWS_BOT_TOKEN', '') else None,
            llm=LLMConfig(
                api_key=google_api_key,
                model=os.getenv('LLM_MODEL', os.getenv('model', 'gemini-2.0-flash')),
            ),
            database=DatabaseConfig(
                path=os.getenv('DB_PATH', 'github_radar.db'),
            ),
            scoring=ScoringConfig(
                min_score_to_notify=int(os.getenv('MIN_SCORE_TO_NOTIFY', '60')),
                max_results_per_day=int(os.getenv('MAX_RESULTS_PER_DAY', '5')),
            ),
            system=SystemConfig(
                scan_interval_minutes=int(os.getenv('SCAN_INTERVAL', '240')),
                debug=os.getenv('DEBUG', 'True').lower() == 'true',
            ),
        )


config = Config.from_env()
