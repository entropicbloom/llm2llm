"""Embedding commands: embed, trajectories."""

from pathlib import Path

import click
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import cli, console, get_config_and_storage


@cli.command()
@click.option("--llm1", default=None, help="Filter by initiator model")
@click.option("--llm2", default=None, help="Filter by responder model")
@click.option("--model", default="openai/text-embedding-3-small", help="Embedding model")
@click.option("--force", is_flag=True, help="Re-embed conversations that already have embeddings")
def embed(llm1: str | None, llm2: str | None, model: str, force: bool):
    """Generate embeddings for conversation messages."""
    from ..embeddings import EmbeddingProvider, EmbeddingStorage

    config, storage = get_config_and_storage()

    if not config.openrouter_api_key:
        console.print("[red]OPENROUTER_API_KEY not set in .env[/red]")
        raise click.Abort()

    provider = EmbeddingProvider(config.openrouter_api_key)
    emb_storage = EmbeddingStorage(config.conversations_dir)

    # Get conversations to embed
    conversations = storage.list_conversations(
        llm1_model=llm1, llm2_model=llm2, limit=1000
    )

    if not force:
        conversations = [c for c in conversations if not emb_storage.has_embeddings(c["id"])]

    if not conversations:
        console.print("[dim]No conversations need embedding.[/dim]")
        return

    console.print(f"\n[bold]Embedding {len(conversations)} conversations[/bold] with {model}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for conv_meta in conversations:
            conv_id = conv_meta["id"]
            task = progress.add_task(f"Embedding {conv_id[:8]}...", total=None)
            try:
                conversation = storage.load(conv_id)
                if not conversation or not conversation.messages:
                    progress.remove_task(task)
                    continue

                texts = [msg.content for msg in conversation.messages]
                embeddings = provider.embed(texts, model=model)

                messages = []
                for msg, emb in zip(conversation.messages, embeddings):
                    messages.append({
                        "turn_number": msg.turn_number,
                        "participant_role": msg.participant_role.value,
                        "embedding": emb,
                    })

                emb_storage.save_embeddings(conv_id, model, messages)
                console.print(f"  [green]{conv_id[:8]}[/green]: {len(texts)} messages embedded")
            except Exception as e:
                console.print(f"  [red]{conv_id[:8]}[/red]: {e}")
            progress.remove_task(task)

    console.print("\n[green]Embedding complete![/green]")


@cli.command()
@click.option("--method", default="umap", type=click.Choice(["umap", "pca"]), help="Reduction method")
@click.option("--output", "-o", default="data/trajectories.json", help="Output JSON path")
def trajectories(method: str, output: str):
    """Reduce embeddings to 2D trajectory coordinates."""
    import json
    from ..embeddings import reduce_embeddings

    config, storage = get_config_and_storage()
    output_path = Path(output)

    console.print(f"[bold]Reducing embeddings to 2D[/bold] (method: {method})")

    result = reduce_embeddings(config.conversations_dir, method=method)

    if not result:
        console.print("[dim]No embeddings found. Run 'llm2llm embed' first.[/dim]")
        return

    total_points = sum(len(v["points"]) for v in result.values())
    console.print(f"  {len(result)} conversations, {total_points} points")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f)

    console.print(f"[green]Trajectories written to: {output_path}[/green]")
