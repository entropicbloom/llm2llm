"""Conversation CRUD commands: run, batch, list, continue, view, delete."""

import click
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import DEFAULT_TURNS
from ..conversation import ConversationEngine, ConversationStatus
from ..models import BaseLLMProvider
from . import cli, console, get_config_and_storage, resolve_conversation_id, _ensure_providers_registered


@cli.command()
def models():
    """List all available models."""
    _ensure_providers_registered()

    all_models = BaseLLMProvider.get_all_models()

    table = Table(title="Available Models")
    table.add_column("Model ID", style="cyan")

    for model_id in sorted(all_models):
        table.add_row(model_id)

    console.print(table)


@cli.command()
@click.option("--llm1", required=True, help="Model ID for the initiator")
@click.option("--llm2", required=True, help="Model ID for the responder")
@click.option("--turns", default=DEFAULT_TURNS, help=f"Number of turns (default: {DEFAULT_TURNS})")
def run(llm1: str, llm2: str, turns: int):
    """Run a new conversation between two LLMs."""
    _ensure_providers_registered()

    config, storage = get_config_and_storage()
    engine = ConversationEngine(config, storage)

    console.print(f"\n[bold]Starting conversation[/bold]")
    console.print(f"  LLM1 (initiator): [cyan]{llm1}[/cyan]")
    console.print(f"  LLM2 (responder): [cyan]{llm2}[/cyan]")
    console.print(f"  Turns: {turns}\n")

    def on_message(turn: int, model_id: str, content: str):
        role_label = "[green]LLM1[/green]" if turn % 2 == 1 else "[blue]LLM2[/blue]"
        console.print(f"[dim]Turn {turn}[/dim] {role_label} ({model_id}):")
        console.print(Panel(content, border_style="dim"))

    try:
        conversation = engine.start_conversation(
            llm1_model=llm1,
            llm2_model=llm2,
            max_turns=turns,
            on_message=on_message,
        )
        console.print(f"\n[green]Conversation completed![/green]")
        console.print(f"ID: [cyan]{conversation.id}[/cyan]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option("--llm1", required=True, help="Model ID for the initiator")
@click.option("--llm2", required=True, help="Model ID for the responder")
@click.option("--count", required=True, type=int, help="Number of conversations to run")
@click.option("--turns", default=DEFAULT_TURNS, help=f"Turns per conversation (default: {DEFAULT_TURNS})")
def batch(llm1: str, llm2: str, count: int, turns: int):
    """Run multiple conversations for the same LLM pair."""
    _ensure_providers_registered()

    config, storage = get_config_and_storage()
    engine = ConversationEngine(config, storage)

    console.print(f"\n[bold]Starting batch of {count} conversations[/bold]")
    console.print(f"  LLM1 (initiator): [cyan]{llm1}[/cyan]")
    console.print(f"  LLM2 (responder): [cyan]{llm2}[/cyan]")
    console.print(f"  Turns per conversation: {turns}\n")

    completed = []
    failed = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i in range(count):
            task_desc = f"Conversation {i + 1}/{count}"
            progress.add_task(description=task_desc, total=None)

            try:
                conversation = engine.start_conversation(
                    llm1_model=llm1,
                    llm2_model=llm2,
                    max_turns=turns,
                )
                completed.append(conversation.id)
                console.print(f"  [green]#{i + 1}[/green] completed: {conversation.id}")
            except Exception as e:
                failed.append(str(e))
                console.print(f"  [red]#{i + 1}[/red] failed: {e}")

    console.print(f"\n[bold]Batch complete[/bold]")
    console.print(f"  Completed: [green]{len(completed)}[/green]")
    console.print(f"  Failed: [red]{len(failed)}[/red]")


@cli.command("list")
@click.option("--llm1", default=None, help="Filter by initiator model")
@click.option("--llm2", default=None, help="Filter by responder model")
@click.option("--status", default=None, type=click.Choice(["active", "completed", "paused", "analyzed"]))
@click.option("--limit", default=50, help="Maximum number of results")
def list_conversations(llm1: str | None, llm2: str | None, status: str | None, limit: int):
    """List conversations."""
    config, storage = get_config_and_storage()

    status_enum = ConversationStatus(status) if status else None
    conversations = storage.list_conversations(
        llm1_model=llm1,
        llm2_model=llm2,
        status=status_enum,
        limit=limit,
    )

    if not conversations:
        console.print("[dim]No conversations found.[/dim]")
        return

    table = Table(title=f"Conversations ({len(conversations)})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("LLM1 (Initiator)", style="green")
    table.add_column("LLM2 (Responder)", style="blue")
    table.add_column("Turns", justify="right")
    table.add_column("Status")
    table.add_column("Updated", style="dim")

    for conv in conversations:
        # Shorten model names for display
        llm1_short = conv["llm1_model"].split("-")[0] + "..." if len(conv["llm1_model"]) > 20 else conv["llm1_model"]
        llm2_short = conv["llm2_model"].split("-")[0] + "..." if len(conv["llm2_model"]) > 20 else conv["llm2_model"]

        status_style = {
            "active": "yellow",
            "completed": "green",
            "paused": "blue",
            "analyzed": "magenta",
        }.get(conv["status"], "white")

        table.add_row(
            conv["id"][:8] + "...",
            llm1_short,
            llm2_short,
            str(conv["turn_count"]),
            f"[{status_style}]{conv['status']}[/{status_style}]",
            conv["updated_at"][:10],
        )

    console.print(table)


@cli.command("continue")
@click.argument("conversation_id")
@click.option("--turns", default=10, help="Number of additional turns")
def continue_conversation(conversation_id: str, turns: int):
    """Continue an existing conversation."""
    _ensure_providers_registered()

    config, storage = get_config_and_storage()
    engine = ConversationEngine(config, storage)

    full_id = resolve_conversation_id(storage, conversation_id)
    console.print(f"\n[bold]Continuing conversation[/bold]: {full_id}")
    console.print(f"  Additional turns: {turns}\n")

    def on_message(turn: int, model_id: str, content: str):
        role_label = "[green]LLM1[/green]" if turn % 2 == 1 else "[blue]LLM2[/blue]"
        console.print(f"[dim]Turn {turn}[/dim] {role_label} ({model_id}):")
        console.print(Panel(content, border_style="dim"))

    try:
        conversation = engine.continue_conversation(
            conversation_id=full_id,
            additional_turns=turns,
            on_message=on_message,
        )
        if conversation:
            console.print(f"\n[green]Conversation continued![/green]")
            console.print(f"Total turns: {conversation.turn_count}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("conversation_id")
@click.option("--tail", default=None, type=int, help="Show only last N messages")
def view(conversation_id: str, tail: int | None):
    """View a conversation."""
    config, storage = get_config_and_storage()

    full_id = resolve_conversation_id(storage, conversation_id)
    conversation = storage.load(full_id)

    if not conversation:
        console.print(f"[red]Could not load conversation: {full_id}[/red]")
        raise click.Abort()

    console.print(f"\n[bold]Conversation[/bold]: {conversation.id}")
    console.print(f"  LLM1: [green]{conversation.llm1_model}[/green]")
    console.print(f"  LLM2: [blue]{conversation.llm2_model}[/blue]")
    console.print(f"  Status: {conversation.status.value}")
    console.print(f"  Turns: {conversation.turn_count}")
    console.print()

    messages = conversation.messages
    if tail:
        messages = messages[-tail:]
        console.print(f"[dim]Showing last {len(messages)} messages[/dim]\n")

    for msg in messages:
        if msg.participant_role.value == "initiator":
            role_label = "[green]LLM1[/green]"
            border_style = "green"
        else:
            role_label = "[blue]LLM2[/blue]"
            border_style = "blue"

        console.print(f"[dim]Turn {msg.turn_number}[/dim] {role_label}:")
        console.print(Panel(msg.content, border_style=border_style))


@cli.command()
@click.argument("conversation_id")
@click.confirmation_option(prompt="Are you sure you want to delete this conversation?")
def delete(conversation_id: str):
    """Delete a conversation."""
    config, storage = get_config_and_storage()

    full_id = resolve_conversation_id(storage, conversation_id)
    if storage.delete(full_id):
        console.print(f"[green]Deleted conversation: {full_id}[/green]")
    else:
        console.print(f"[red]Failed to delete conversation[/red]")
