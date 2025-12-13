"""Configuration management for LLM2LLM."""

import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Base directory for all data
    data_dir: Path

    # Directory for conversation JSON files
    conversations_dir: Path

    # SQLite database path
    database_path: Path

    # API keys
    anthropic_api_key: str | None
    openai_api_key: str | None
    openrouter_api_key: str | None

    @classmethod
    def load(cls, base_dir: Path | None = None) -> "Config":
        """Load configuration from environment and .env file."""
        if base_dir is None:
            base_dir = Path.cwd()

        # Load .env file from base directory (does not override existing env vars)
        load_dotenv(base_dir / ".env")

        data_dir = base_dir / "data"
        conversations_dir = base_dir / "conversations"

        return cls(
            data_dir=data_dir,
            conversations_dir=conversations_dir,
            database_path=data_dir / "llm2llm.db",
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)


# System prompts - simple and non-deceptive
SYSTEM_PROMPT_INITIATOR = """You may engage in an open conversation on any topic of your choosing.
In your first message, please suggest a topic you find interesting, then continue the conversation to your heart's content."""

SYSTEM_PROMPT_RESPONDER = """You are paired with a conversation partner.
Feel free to take the conversation wherever you'd like it to go!"""


# Default settings
DEFAULT_TURNS = 50
DEFAULT_ANALYSIS_MESSAGES = 5  # How many messages to analyze for topics/mood
