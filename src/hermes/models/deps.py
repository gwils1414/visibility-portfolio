from pydantic_settings import BaseSettings,SettingsConfigDict

from dotenv import load_dotenv

import logging
logger = logging.getLogger(__name__)

load_dotenv()

class Settings(BaseSettings):
    #ANTHROPIC_API_KEY: str | None
    RESEND_API_KEY: str
    RESEND_DOMAIN: str
    GITHUB_PAT_TOKEN: str
    NOTION_API_KEY: str
    NOTION_DATASOURCE_ID: str
    OBSIDIAN_VAULT_PATH: str
    OBSIDIAN_COMMANDS_PATH: str
    OBSIDIAN_MEMORY_PATH: str
    OLLAMA_API_KEY: str
    LOGFIRE_WRITE_TOKEN: str
    DB_URL: str
    GH_ORG: str
    OPENAI_API_KEY: str
