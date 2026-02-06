"""CLI for LLM2LLM conversation playground."""

import click
from rich.console import Console

from ..config import Config
from ..conversation import ConversationStorage

console = Console()


def get_config_and_storage() -> tuple[Config, ConversationStorage]:
    """Initialize config and storage."""
    config = Config.load()
    config.ensure_directories()
    storage = ConversationStorage(config.database_path, config.conversations_dir)
    return config, storage


def resolve_conversation_id(storage: ConversationStorage, partial_id: str) -> str:
    """Resolve a partial conversation ID to its full ID.

    Raises click.Abort if no match or multiple matches found.
    """
    all_convs = storage.list_conversations(limit=1000)
    matches = [c for c in all_convs if c["id"].startswith(partial_id)]

    if not matches:
        console.print(f"[red]No conversation found matching: {partial_id}[/red]")
        raise click.Abort()
    if len(matches) > 1:
        console.print(f"[red]Multiple matches found. Please be more specific:[/red]")
        for m in matches:
            console.print(f"  {m['id']}")
        raise click.Abort()

    return matches[0]["id"]


def _ensure_providers_registered():
    """Ensure LLM providers are registered by importing them."""
    from ..models import AnthropicProvider  # noqa: F401


@click.group()
@click.version_option()
def cli():
    """LLM2LLM - Experimental playground for LLM-to-LLM conversations."""
    pass


# Import submodules to register commands with the cli group
from . import conversations  # noqa: E402, F401
from . import analysis  # noqa: E402, F401
from . import embeddings  # noqa: E402, F401
from . import dashboard  # noqa: E402, F401
