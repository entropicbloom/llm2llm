"""Dashboard command."""

from pathlib import Path

import click

from . import cli, console, get_config_and_storage


@cli.command()
@click.option("--output", "-o", default="dashboard.html", help="Output file path")
@click.option("--open", "open_browser", is_flag=True, help="Open in browser after generating")
def dashboard(output: str, open_browser: bool):
    """Generate a static HTML dashboard."""
    import subprocess
    from ..dashboard.html_generator import write_dashboard

    config, storage = get_config_and_storage()
    output_path = Path(output)

    # Build JS bundle first (skip if npm not available)
    project_root = Path(__file__).parent.parent.parent
    try:
        console.print("[dim]Building JS bundle...[/dim]")
        result = subprocess.run(
            ["npm", "run", "build:dashboard"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[yellow]JS build failed (using existing bundle):[/yellow] {result.stderr}")
    except FileNotFoundError:
        console.print("[yellow]npm not found, using existing JS bundle[/yellow]")

    console.print("[bold]Generating dashboard...[/bold]")
    write_dashboard(output_path, config, storage)
    console.print(f"[green]Dashboard written to: {output_path.absolute()}[/green]")

    if open_browser:
        import webbrowser
        webbrowser.open(f"file://{output_path.absolute()}")
