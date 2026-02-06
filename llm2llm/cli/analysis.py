"""Analysis commands: analyze, annotate, report, titles."""

import click
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import cli, console, get_config_and_storage, resolve_conversation_id, _ensure_providers_registered


@cli.command()
@click.option("--llm1", default=None, help="Filter by initiator model")
@click.option("--llm2", default=None, help="Filter by responder model")
@click.option("--model", default=None, help="Model to use for analysis (default: claude-sonnet-4-5-20250929)")
@click.option("--start", default=-5, type=int, help="Start index for message segment (default: -5, last 5)")
@click.option("--end", default=None, type=int, help="End index for message segment (default: None, to end)")
def analyze(llm1: str | None, llm2: str | None, model: str | None, start: int, end: int | None):
    """Analyze conversation segments for topics and mood."""
    _ensure_providers_registered()
    from ..analysis import ConversationAnalyzer

    config, storage = get_config_and_storage()
    analyzer = ConversationAnalyzer(config, storage, analysis_model=model)

    conversations = list(storage.get_conversations_for_analysis(llm1, llm2, start, end))

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
    from ..analysis.analyzer import AnalysisResult

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
            f"  \u2022 {topic} ({score:.0%})"
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
                f"[green]{result['llm1_model']}[/green] \u2192 [blue]{result['llm2_model']}[/blue]\n"
                f"Segment: {segment_desc}\n"
                f"Conversations: {result['conversation_count']}\n\n"
                f"[bold]Top Topics:[/bold]\n{topics_str}\n\n"
                f"[bold]Mood:[/bold]\n{mood_str}"
            ),
            title="LLM Pair Analysis",
        ))


@cli.command()
@click.option("--model", default="claude-haiku-4-5-20251001", help="Model to use for title generation")
def titles(model: str):
    """Generate titles for conversations that don't have them."""
    from ..analysis.title_generator import generate_title

    config, storage = get_config_and_storage()

    conversation_ids = storage.get_conversations_without_titles()

    if not conversation_ids:
        console.print("[dim]All conversations have titles.[/dim]")
        return

    console.print(f"\n[bold]Generating titles for {len(conversation_ids)} conversations[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for conv_id in conversation_ids:
            task = progress.add_task(f"Titling {conv_id[:8]}...", total=None)
            try:
                conversation = storage.load(conv_id)
                if not conversation:
                    continue

                messages = [{"role": m.participant_role.value, "content": m.content} for m in conversation.messages]
                title = generate_title(messages, model=model)
                storage.save_title(conv_id, title)
                console.print(f"  [green]{conv_id[:8]}[/green]: {title}")
            except Exception as e:
                console.print(f"  [red]{conv_id[:8]}[/red]: {e}")
            progress.remove_task(task)

    console.print("\n[green]Done![/green]")
