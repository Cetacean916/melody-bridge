"""YTM matching engine: 3-stage search with artist mapping."""

import json
import re
import time
from pathlib import Path

import typer
from ytmusicapi import YTMusic

from .artist_map import get_search_variants
from .models import (
    Checkpoint,
    MatchConfidence,
    MatchResult,
    MatchStrategy,
    MelonTrack,
)


def _clean_title(title: str) -> str:
    """Remove parenthetical content and extra whitespace."""
    return re.sub(r"\s*[\(\[].*?[\)\]]", "", title).strip()


def _short_title(title: str) -> str:
    """Take the part before '-' or '–' if present."""
    for sep in [" - ", " – ", "-"]:
        if sep in title:
            return title.split(sep)[0].strip()
    return title


def _normalize(s: str) -> str:
    """Normalize for comparison."""
    return re.sub(r"\s+", " ", s.lower().strip())


def _artist_matches(result_artist: str, search_artist: str) -> bool:
    """Check if result artist matches the search artist."""
    ra = _normalize(result_artist)
    sa = _normalize(search_artist)

    # Direct match
    if sa in ra or ra in sa:
        return True

    # Check all variants
    for variant in get_search_variants(search_artist):
        if _normalize(variant) in ra:
            return True

    return False


def _pick_best(results: list[dict], artist: str, title: str) -> MatchResult | None:
    """Pick the best match from search results."""
    if not results:
        return None

    target_title = _normalize(_clean_title(title))
    target_title_raw = _normalize(title)

    for r in results:
        rtitle = _normalize(r.get("title", ""))
        rartists = ", ".join(a.get("name", "") for a in r.get("artists", []))

        # Check artist match
        if rartists and not _artist_matches(rartists, artist):
            # For videos, also check channel
            channel = r.get("channel", "")
            if channel:
                combined = _normalize(f"{rartists} {channel}")
                if not _artist_matches(combined, artist):
                    continue
            else:
                continue

        # Check title match
        clean_rtitle = _normalize(_clean_title(rtitle))
        if (
            target_title in clean_rtitle
            or clean_rtitle in target_title
            or target_title_raw in rtitle
        ):
            vid = r.get("videoId")
            if vid:
                return MatchResult(
                    melon=MelonTrack(title=title, artist=artist),
                    video_id=vid,
                    yt_title=rtitle,
                    yt_artist=rartists,
                    confidence=MatchConfidence.HIGH,
                )

    # Fallback: take first result with matching artist (looser title match)
    for r in results:
        rartists = ", ".join(a.get("name", "") for a in r.get("artists", []))
        if rartists and _artist_matches(rartists, artist):
            vid = r.get("videoId")
            if vid:
                return MatchResult(
                    melon=MelonTrack(title=title, artist=artist),
                    video_id=vid,
                    yt_title=r.get("title", ""),
                    yt_artist=rartists,
                    confidence=MatchConfidence.MEDIUM,
                )

    return None


def match_track(yt: YTMusic, track: MelonTrack) -> MatchResult:
    """Match a single MelonTrack to a YTM video ID using 3-stage strategy."""
    artist = track.artist
    title = track.title
    variants = get_search_variants(artist)

    # Stage 1: Original query with filter="songs"
    for a in variants:
        query = f"{a} {title}"
        try:
            results = yt.search(query, filter="songs")
        except Exception:
            results = []
        if results:
            match = _pick_best(results, artist, title)
            if match and match.confidence == MatchConfidence.HIGH:
                match.strategy = MatchStrategy.ORIGINAL
                return match
        time.sleep(0.3)

    # Stage 2: Clean title (remove parentheses)
    clean = _clean_title(title)
    if clean != title:
        for a in variants:
            query = f"{a} {clean}"
            try:
                results = yt.search(query, filter="songs")
            except Exception:
                results = []
            if results:
                match = _pick_best(results, artist, title)
                if match and match.confidence in (
                    MatchConfidence.HIGH,
                    MatchConfidence.MEDIUM,
                ):
                    match.strategy = MatchStrategy.PARENS_REMOVED
                    return match
            time.sleep(0.3)

    # Stage 3: Short title + unfiltered search
    short = _short_title(clean)
    for a in variants:
        queries = [f"{a} {short}"]
        if short != clean:
            queries.append(f"{a} {clean}")

        for query in queries:
            # Try without filter
            try:
                results = yt.search(query)
            except Exception:
                results = []
            if results:
                match = _pick_best(results, artist, title)
                if match:
                    match.strategy = MatchStrategy.UNFILTERED
                    return match
            time.sleep(0.3)

    return MatchResult(
        melon=track,
        not_found=True,
    )


def _load_melon_tracks(input_dir: Path) -> list[MelonTrack]:
    """Load all MelonTrack from scraped JSON files."""
    tracks: list[MelonTrack] = []

    # Liked songs
    liked_file = input_dir / "liked_songs.json"
    if liked_file.exists():
        for t in json.load(open(liked_file)):
            tracks.append(MelonTrack(**t))

    # Playlist songs
    ps_dir = input_dir / "playlist_songs"
    if ps_dir.exists():
        for f in sorted(ps_dir.glob("*.json")):
            for t in json.load(open(f)):
                tracks.append(MelonTrack(**t))

    # Deduplicate by (title, artist)
    seen = set()
    unique = []
    for t in tracks:
        key = (_normalize(t.title), _normalize(t.artist))
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return unique


def _load_checkpoint(cp_path: Path) -> Checkpoint | None:
    if not cp_path.exists():
        return None
    data = json.load(open(cp_path))
    return Checkpoint(**data)


def _save_checkpoint(cp: Checkpoint, cp_path: Path) -> None:
    data = {
        "key": cp.key,
        "total": cp.total,
        "processed": cp.processed,
        "matched": cp.matched,
        "not_found": cp.not_found,
        "done": cp.done,
        "processed_indices": cp.processed_indices,
        "not_found_items": cp.not_found_items,
        "playlist_id": cp.playlist_id,
    }
    with open(cp_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def match_all(
    input_dir: Path,
    output: Path,
    state_dir: Path,
    resume: bool = True,
) -> None:
    """Match all Melon tracks to YTM video IDs."""
    from .auth import get_yt

    yt = get_yt(state_dir)
    tracks = _load_melon_tracks(input_dir)
    typer.echo(f"Loaded {len(tracks)} unique tracks")

    # Load existing results
    results: list[dict] = []
    cp_path = state_dir / "match_checkpoint.json"
    cp = _load_checkpoint(cp_path) if resume else None

    if cp and cp.key == str(input_dir):
        # Resume: load previous results
        if output.exists():
            results = json.load(open(output))
        done_indices = set(cp.processed_indices)
        typer.echo(
            f"Resuming: {cp.processed}/{cp.total} already processed "
            f"({cp.matched} matched, {cp.not_found} not found)"
        )
    else:
        cp = Checkpoint(key=str(input_dir), total=len(tracks))
        done_indices = set()

    # Process remaining
    for i, track in enumerate(tracks):
        if i in done_indices:
            continue

        result = match_track(yt, track)
        result_dict = {
            "melon": vars(result.melon),
            "video_id": result.video_id,
            "yt_title": result.yt_title,
            "yt_artist": result.yt_artist,
            "confidence": result.confidence.value,
            "strategy": result.strategy.value,
            "not_found": result.not_found,
        }
        results.append(result_dict)

        cp.processed = len(done_indices) + len(
            [r for r in results if results.index(r) >= len(done_indices)]
        )
        cp.processed_indices.append(i)
        if result.not_found:
            cp.not_found += 1
            cp.not_found_items.append(f"{track.artist} - {track.title}")
        else:
            cp.matched += 1

        # Save checkpoint every 50 tracks
        if (i + 1) % 50 == 0:
            with open(output, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            _save_checkpoint(cp, cp_path)
            typer.echo(
                f"  Progress: {cp.processed}/{cp.total} "
                f"(matched: {cp.matched}, not found: {cp.not_found})"
            )

        time.sleep(0.5)

    # Final save
    with open(output, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    cp.done = True
    _save_checkpoint(cp, cp_path)

    typer.echo(f"\nMatching complete:")
    typer.echo(f"  Total: {cp.total}")
    typer.echo(f"  Matched: {cp.matched}")
    typer.echo(f"  Not found: {cp.not_found}")
    if cp.not_found_items:
        typer.echo(f"\nNot found ({len(cp.not_found_items)}):")
        for item in cp.not_found_items[:30]:
            typer.echo(f"  - {item}")
        if len(cp.not_found_items) > 30:
            typer.echo(f"  ... and {len(cp.not_found_items) - 30} more")
