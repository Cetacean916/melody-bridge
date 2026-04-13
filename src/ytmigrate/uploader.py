"""Playlist creation and upload with checkpoint/resume."""

import json
import time
from pathlib import Path

import typer
from ytmusicapi import YTMusic


def _chunk(lst: list, size: int) -> list[list]:
    """Split list into chunks."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def create_playlists(
    matched_file: Path,
    name: str,
    description: str,
    state_dir: Path,
    dry_run: bool = False,
) -> None:
    """Create YTM playlists from matched results."""
    from .auth import get_yt

    if not matched_file.exists():
        typer.echo(f"File not found: {matched_file}", err=True)
        raise typer.Exit(1)

    results = json.load(open(matched_file))

    # Separate found vs not found
    found = [r for r in results if not r.get("not_found") and r.get("video_id")]
    not_found = [r for r in results if r.get("not_found")]

    typer.echo(f"Matched: {len(found)}, Not found: {len(not_found)}")

    if dry_run:
        typer.echo("\n--- DRY RUN ---")
        typer.echo(f"Would create playlist: {name}")
        typer.echo(f"Tracks to add: {len(found)}")
        for r in found[:10]:
            m = r["melon"]
            typer.echo(f"  {m['artist']} - {m['title']} → {r['video_id']}")
        if len(found) > 10:
            typer.echo(f"  ... and {len(found) - 10} more")
        return

    yt = get_yt(state_dir)

    # Check for existing playlist with same name
    existing_pl = None
    try:
        library = yt.get_library_playlists(limit=100)
        for pl in library:
            if pl.get("title") == name:
                existing_pl = pl
                break
    except Exception:
        pass

    if existing_pl:
        pl_id = existing_pl["playlistId"]
        typer.echo(f"Using existing playlist: {name} ({pl_id})")

        # Get existing tracks to avoid duplicates
        try:
            pl_data = yt.get_playlist(pl_id, limit=5000)
            existing_vids = {
                t.get("videoId")
                for t in pl_data.get("tracks", [])
                if t.get("videoId")
            }
        except Exception:
            existing_vids = set()

        new_tracks = [r for r in found if r["video_id"] not in existing_vids]
        typer.echo(
            f"  Already in playlist: {len(found) - len(new_tracks)}, "
            f"New: {len(new_tracks)}"
        )
    else:
        pl_id = yt.create_playlist(name, description)
        typer.echo(f"Created playlist: {name} ({pl_id})")
        new_tracks = found

    if not new_tracks:
        typer.echo("No new tracks to add.")
        return

    # Add tracks in batches of 50
    video_ids = [r["video_id"] for r in new_tracks]
    batches = _chunk(video_ids, 50)
    added = 0

    for i, batch in enumerate(batches):
        try:
            yt.add_playlist_items(pl_id, batch)
            added += len(batch)
            typer.echo(f"  Batch {i+1}/{len(batches)}: +{len(batch)} (total: {added})")
        except Exception as e:
            err_str = str(e)
            if "401" in err_str:
                typer.echo("  Auth expired! Refreshing...", err=True)
                from .auth import refresh
                yt = refresh(state_dir)
                if yt:
                    try:
                        yt.add_playlist_items(pl_id, batch)
                        added += len(batch)
                        typer.echo(f"  Retry OK: batch {i+1}")
                    except Exception as e2:
                        typer.echo(f"  Retry failed: {e2}", err=True)
                else:
                    typer.echo("  Refresh failed. Stopping.", err=True)
                    break
            else:
                typer.echo(f"  Error on batch {i+1}: {e}", err=True)

        time.sleep(1)

    typer.echo(f"\nDone! Added {added} tracks to '{name}'")

    # Report not found
    if not_found:
        nf_file = matched_file.parent / "not_found.txt"
        with open(nf_file, "w") as f:
            for r in not_found:
                m = r["melon"]
                f.write(f"{m['artist']} - {m['title']}\n")
        typer.echo(f"Not found: {len(not_found)} tracks → {nf_file}")


def report(matched_file: Path) -> None:
    """Print a summary report of matching results."""
    if not matched_file.exists():
        typer.echo(f"File not found: {matched_file}", err=True)
        raise typer.Exit(1)

    results = json.load(open(matched_file))

    found = [r for r in results if not r.get("not_found") and r.get("video_id")]
    not_found = [r for r in results if r.get("not_found")]

    # Confidence breakdown
    by_conf: dict[str, int] = {}
    by_strategy: dict[str, int] = {}
    for r in found:
        c = r.get("confidence", "unknown")
        by_conf[c] = by_conf.get(c, 0) + 1
        s = r.get("strategy", "unknown")
        by_strategy[s] = by_strategy.get(s, 0) + 1

    typer.echo(f"=== Match Report ===")
    typer.echo(f"Total: {len(results)}")
    typer.echo(f"Matched: {len(found)} ({len(found)/len(results)*100:.1f}%)")
    typer.echo(f"Not found: {len(not_found)}")
    typer.echo(f"\nConfidence:")
    for k, v in sorted(by_conf.items()):
        typer.echo(f"  {k}: {v}")
    typer.echo(f"\nStrategy:")
    for k, v in sorted(by_strategy.items()):
        typer.echo(f"  {k}: {v}")

    if not_found:
        typer.echo(f"\nNot found ({len(not_found)}):")
        for r in not_found[:50]:
            m = r["melon"]
            typer.echo(f"  {m['artist']} - {m['title']}")
