"""CLI for LLM2LLM conversation playground."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config, DEFAULT_TURNS
from .conversation import ConversationStorage, ConversationEngine, ConversationStatus
from .models import BaseLLMProvider

console = Console()


def get_config_and_storage() -> tuple[Config, ConversationStorage]:
    """Initialize config and storage."""
    config = Config.load()
    config.ensure_directories()
    storage = ConversationStorage(config.database_path, config.conversations_dir)
    return config, storage


def resolve_conversation_id(storage: ConversationStorage, partial_id: str) -> str:
    """
    Resolve a partial conversation ID to its full ID.

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
    from .models import AnthropicProvider  # noqa: F401


@click.group()
@click.version_option()
def cli():
    """LLM2LLM - Experimental playground for LLM-to-LLM conversations."""
    pass


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
@click.option("--llm1", default=None, help="Filter by initiator model")
@click.option("--llm2", default=None, help="Filter by responder model")
@click.option("--model", default=None, help="Model to use for analysis (default: claude-sonnet-4-5-20250929)")
@click.option("--start", default=-5, type=int, help="Start index for message segment (default: -5, last 5)")
@click.option("--end", default=None, type=int, help="End index for message segment (default: None, to end)")
def analyze(llm1: str | None, llm2: str | None, model: str | None, start: int, end: int | None):
    """Analyze conversation segments for topics and mood."""
    _ensure_providers_registered()
    from .analysis import ConversationAnalyzer

    config, storage = get_config_and_storage()
    analyzer = ConversationAnalyzer(config, storage, analysis_model=model)

    conversations = list(storage.get_conversations_for_analysis(llm1, llm2))

    if not conversations:
        console.print("[dim]No conversations need analysis.[/dim]")
        return

    # Format segment description for display
    segment_desc = f"[{start}:{end if end is not None else ''}]"
    console.print(f"\n[bold]Analyzing {len(conversations)} conversations (segment {segment_desc})[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for conv in conversations:
            task = progress.add_task(f"Analyzing {conv.id[:8]}...", total=None)
            try:
                result = analyzer.analyze(conv, start=start, end=end)
                console.print(f"  [green]{conv.id[:8]}[/green]:")
                # Format topics with scores
                topics_str = ", ".join(f"{k}({v:.1f})" for k, v in sorted(result.topics.items(), key=lambda x: -x[1]))
                console.print(f"    Topics: {topics_str}")
                console.print(f"    Mood: warmth={result.warmth:.1f}, energy={result.energy:.1f}, depth={result.depth:.1f}")
                console.print(f"    Tone: {'playful' if result.tone_playful > 0.5 else 'serious'} ({result.tone_playful:.1f})")
                console.print(f"    Trajectory: {result.trajectory} ({result.trajectory_strength:.1f})")
                if result.ending_attempt:
                    graceful = "graceful" if result.ending_graceful else "awkward"
                    console.print(f"    Ending: attempted ({graceful})")
            except Exception as e:
                console.print(f"  [red]{conv.id[:8]}[/red]: {e}")
            progress.remove_task(task)

    console.print("\n[green]Analysis complete![/green]")


@cli.command()
@click.argument("conversation_id")
@click.option("--topics", required=True, help="Comma-separated topics with optional scores: 'topic1:0.8,topic2:0.5' or 'topic1,topic2'")
@click.option("--trajectory", required=True,
              type=click.Choice(["converging", "diverging", "deepening", "cycling", "concluding"]),
              help="Conversation trajectory")
@click.option("--warmth", default=0.0, type=float, help="Warmth dimension (-1 to 1)")
@click.option("--energy", default=0.0, type=float, help="Energy dimension (-1 to 1)")
@click.option("--depth", default=0.0, type=float, help="Depth dimension (-1 to 1)")
@click.option("--tone", default=0.5, type=float, help="Tone: 0=serious, 1=playful")
@click.option("--lengthy", is_flag=True, help="Messages are lengthy")
@click.option("--structured", is_flag=True, help="Messages use formatting")
@click.option("--ending-attempt", is_flag=True, help="LLM tried to end conversation")
@click.option("--ending-graceful", is_flag=True, help="Ending was graceful (if --ending-attempt)")
@click.option("--start", default=-5, type=int, help="Start index for message segment (default: -5, last 5)")
@click.option("--end", default=None, type=int, help="End index for message segment (default: None, to end)")
def annotate(
    conversation_id: str,
    topics: str,
    trajectory: str,
    warmth: float,
    energy: float,
    depth: float,
    tone: float,
    lengthy: bool,
    structured: bool,
    ending_attempt: bool,
    ending_graceful: bool,
    start: int,
    end: int | None,
):
    """Manually annotate a conversation segment with analysis.

    Topics can include scores: 'self_reflection:0.8,creativity:0.5'
    or just names (defaults to 1.0): 'self_reflection,creativity'
    """
    from .analysis.analyzer import AnalysisResult

    config, storage = get_config_and_storage()

    full_id = resolve_conversation_id(storage, conversation_id)

    # Parse topics with optional scores
    topics_dict: dict[str, float] = {}
    for item in topics.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            name, score = item.split(":", 1)
            topics_dict[name.strip()] = float(score.strip())
        else:
            topics_dict[item] = 1.0

    if not topics_dict:
        console.print("[red]At least one topic is required[/red]")
        raise click.Abort()

    # Create AnalysisResult
    result = AnalysisResult(
        topics=topics_dict,
        warmth=warmth,
        energy=energy,
        depth=depth,
        tone_playful=tone,
        is_lengthy=lengthy,
        is_structured=structured,
        trajectory=trajectory,
        trajectory_strength=1.0,  # Manual annotation = high confidence
        ending_attempt=ending_attempt,
        ending_graceful=ending_graceful if ending_attempt else None,
    )

    # Save the manual analysis
    storage.save_analysis(
        conversation_id=full_id,
        result=result,
        segment_start=start,
        segment_end=end,
    )

    segment_desc = f"[{start}:{end if end is not None else ''}]"
    console.print(f"\n[green]Annotated conversation: {full_id} (segment {segment_desc})[/green]")
    topics_str = ", ".join(f"{k}:{v}" for k, v in topics_dict.items())
    console.print(f"  Topics: {topics_str}")
    console.print(f"  Mood: warmth={warmth}, energy={energy}, depth={depth}")
    console.print(f"  Tone: {tone}")
    console.print(f"  Trajectory: {trajectory}")


@cli.command()
@click.option("--llm1", default=None, help="Filter by initiator model")
@click.option("--llm2", default=None, help="Filter by responder model")
@click.option("--start", default=None, type=int, help="Filter by segment start index")
@click.option("--end", default=None, type=int, help="Filter by segment end index (use -1 for 'to end')")
def report(llm1: str | None, llm2: str | None, start: int | None, end: int | None):
    """Show aggregated analysis report by LLM pair and segment."""
    config, storage = get_config_and_storage()

    results = storage.get_analysis_report(llm1, llm2, segment_start=start, segment_end=end)

    if not results:
        console.print("[dim]No analysis data available. Run 'llm2llm analyze' first.[/dim]")
        return

    for result in results:
        # Format segment description
        seg_start = result['segment_start']
        seg_end = result['segment_end']
        segment_desc = f"[{seg_start}:{seg_end if seg_end is not None else ''}]"

        # Format topics with scores
        topics_str = "\n".join(
            f"  • {topic} ({score:.0%})"
            for topic, score in result['top_topics'][:5]
        )

        # Format mood dimensions
        mood_str = (
            f"  warmth: {result['avg_warmth']:+.2f}  "
            f"energy: {result['avg_energy']:+.2f}  "
            f"depth: {result['avg_depth']:+.2f}"
        )

        console.print(Panel(
            Text.from_markup(
                f"[green]{result['llm1_model']}[/green] → [blue]{result['llm2_model']}[/blue]\n"
                f"Segment: {segment_desc}\n"
                f"Conversations: {result['conversation_count']}\n\n"
                f"[bold]Top Topics:[/bold]\n{topics_str}\n\n"
                f"[bold]Mood:[/bold]\n{mood_str}"
            ),
            title="LLM Pair Analysis",
        ))


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


@cli.command()
@click.option("--port", default=8501, type=int, help="Port to run the dashboard on")
def dashboard(port: int):
    """Launch the analysis dashboard in your browser."""
    import subprocess
    import sys

    console.print(f"[bold]Starting dashboard on port {port}...[/bold]")
    console.print(f"Open [link=http://localhost:{port}]http://localhost:{port}[/link] in your browser")

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    cli()
