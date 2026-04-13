"""CLI entry point for ytmigrate."""

import typer
from pathlib import Path

app = typer.Typer(
    name="ytmigrate",
    help="Migrate Melon likes and playlists to YouTube Music.",
    no_args_is_help=True,
)

DEFAULT_STATE_DIR = Path("~/.config/ytmigrate").expanduser()


@app.command()
def auth(
    action: str = typer.Argument(help="setup | refresh | check"),
):
    """Manage YTM authentication."""
    from . import auth as auth_mod

    state_dir = DEFAULT_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)

    if action == "setup":
        auth_mod.setup(state_dir)
    elif action == "refresh":
        auth_mod.refresh(state_dir)
    elif action == "check":
        auth_mod.check(state_dir)
    else:
        typer.echo(f"Unknown action: {action}. Use setup, refresh, or check.")
        raise typer.Exit(1)


@app.command()
def import_melon(
    member_key: str = typer.Option(..., help="Melon member key"),
    output: Path = typer.Option(
        Path("melon_data").resolve(),
        help="Output directory for scraped data.",
    ),
    likes: bool = typer.Option(True, help="Scrape liked songs."),
    playlists: bool = typer.Option(True, help="Scrape playlists."),
):
    """Scrape liked songs and playlists from Melon."""
    from .melon import scrape_all

    scrape_all(member_key, output, likes=likes, playlists=playlists)


@app.command()
def match(
    input_dir: Path = typer.Argument(help="Directory with Melon JSON data."),
    output: Path = typer.Option(
        Path("matched.json").resolve(),
        help="Output file for matched results.",
    ),
    resume: bool = typer.Option(True, help="Resume from checkpoint."),
):
    """Match Melon songs to YTM video IDs."""
    from .matcher import match_all

    state_dir = DEFAULT_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    match_all(input_dir, output, state_dir, resume=resume)


@app.command()
def create(
    matched_file: Path = typer.Argument(help="Matched results JSON."),
    name: str = typer.Option("Melon Import", help="Playlist name."),
    description: str = typer.Option(
        "Imported from Melon", help="Playlist description."
    ),
    dry_run: bool = typer.Option(False, help="Preview without creating."),
):
    """Create YTM playlists from matched results."""
    from .uploader import create_playlists

    state_dir = DEFAULT_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    create_playlists(matched_file, name, description, state_dir, dry_run=dry_run)


@app.command()
def report(
    matched_file: Path = typer.Argument(help="Matched results JSON."),
):
    """Show matching report."""
    from .uploader import report as do_report

    do_report(matched_file)


@app.command()
def run(
    member_key: str = typer.Option(..., help="Melon member key"),
    name: str = typer.Option("Melon Import", help="Playlist name."),
    output_dir: Path = typer.Option(
        Path("ytmigrate_work").resolve(),
        help="Working directory.",
    ),
):
    """Full pipeline: import → match → create."""
    from . import auth as auth_mod
    from .melon import scrape_all
    from .matcher import match_all
    from .uploader import create_playlists

    state_dir = DEFAULT_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo("Step 1/3: Checking auth...")
    auth_mod.refresh(state_dir)

    typer.echo("Step 2/3: Importing from Melon...")
    melon_dir = output_dir / "melon_data"
    scrape_all(member_key, melon_dir)

    typer.echo("Step 3/3: Matching and creating playlists...")
    matched_file = output_dir / "matched.json"
    match_all(melon_dir, matched_file, state_dir)
    create_playlists(matched_file, name, "Imported from Melon", state_dir)

    typer.echo("Done!")


if __name__ == "__main__":
    app()
