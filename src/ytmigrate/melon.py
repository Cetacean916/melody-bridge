"""Melon scraper: liked songs and playlists via public AJAX APIs."""

import json
import re
import time
from pathlib import Path

import requests
import typer
from bs4 import BeautifulSoup
from .models import MelonTrack

BASE = "https://www.melon.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.melon.com/",
}


def _fetch_page(url: str, params: dict, retries: int = 3) -> str | None:
    """POST with retries. Returns HTML or None."""
    h = dict(HEADERS)
    h["Referer"] = url.replace("Paging.htm", ".htm").replace("_listPaging", "_list")
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=h, data=params, timeout=20)
            if resp.status_code == 200 and len(resp.text) > 100:
                return resp.text
            typer.echo(f"  Status {resp.status_code} at attempt {attempt+1}", err=True)
        except Exception as e:
            typer.echo(f"  Retry {attempt+1}/{retries}: {e}", err=True)
        time.sleep(2 * (attempt + 1))
    return None


def _parse_songs(html: str) -> list[MelonTrack]:
    """Extract tracks from Melon song table HTML."""
    soup = BeautifulSoup(html, "html.parser")
    tracks = []
    for row in soup.select("table tbody tr"):
        title_el = row.select_one('a[href*="goSongDetail"]')
        artist_el = row.select_one('a[href*="goArtistDetail"]')
        album_el = row.select_one('a[href*="goAlbumDetail"]')
        if title_el:
            title = title_el.text.strip().replace(" 상세정보 페이지 이동", "")
            artist = artist_el.text.strip() if artist_el else ""
            album = album_el.text.strip() if album_el else ""
            tracks.append(MelonTrack(title=title, artist=artist, album=album))
    return tracks


def scrape_likes(member_key: str, output_dir: Path) -> list[MelonTrack]:
    """Scrape all liked songs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "liked_songs.json"

    if out_file.exists():
        existing = [MelonTrack(**t) for t in json.load(open(out_file))]
        if len(existing) >= 2300:
            typer.echo(f"  Already have {len(existing)} liked songs, skipping")
            return existing

    typer.echo("Scraping liked songs...")
    all_tracks: list[MelonTrack] = []
    page_size = 20
    start = 1
    max_songs = 5000  # safety limit

    while start <= max_songs:
        html = _fetch_page(
            f"{BASE}/mymusic/like/mymusiclikesong_listPaging.htm",
            {"memberKey": member_key, "startIndex": str(start), "pageSize": str(page_size)},
        )
        if not html:
            typer.echo(f"  Failed at startIndex={start}", err=True)
            break

        tracks = _parse_songs(html)
        if not tracks:
            break

        all_tracks.extend(tracks)
        typer.echo(f"  Page {start}: +{len(tracks)} (total: {len(all_tracks)})")

        # Checkpoint
        with open(out_file, "w") as f:
            json.dump([vars(t) for t in all_tracks], f, ensure_ascii=False, indent=2)

        start += page_size
        time.sleep(0.3)

    typer.echo(f"  Liked songs: {len(all_tracks)}")
    return all_tracks


def scrape_playlist_list(member_key: str) -> list[dict]:
    """Scrape playlist metadata."""
    html = _fetch_page(
        f"{BASE}/mymusic/playlist/mymusicplaylist_listPaging.htm",
        {"memberKey": member_key, "startIndex": "1", "pageSize": "100"},
    )
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    playlists = []
    for row in soup.select("table tbody tr"):
        name_link = row.select_one('dt a[href*="goPlaylistDetail"]')
        if not name_link:
            continue

        name = name_link.text.strip()
        href = name_link.get("href", "")
        seq_matches = re.findall(r"'(\d+)'", href)
        seq = seq_matches[-1] if seq_matches else ""

        count_el = row.select_one("p")
        count_match = re.search(r"총\s*(\d+)곡", count_el.text if count_el else "")
        song_count = int(count_match.group(1)) if count_match else 0

        playlists.append({"seq": seq, "name": name, "song_count": song_count})

    typer.echo(f"  Found {len(playlists)} playlists")
    return playlists


def scrape_playlist_songs(
    member_key: str, playlists: list[dict], output_dir: Path
) -> dict[str, list[MelonTrack]]:
    """Scrape songs for each playlist."""
    songs_dir = output_dir / "playlist_songs"
    songs_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[MelonTrack]] = {}

    for i, pl in enumerate(playlists):
        seq = pl["seq"]
        name = pl["name"]
        count = pl["song_count"]
        out_file = songs_dir / f"{seq}.json"

        if out_file.exists():
            existing = [MelonTrack(**t) for t in json.load(open(out_file))]
            if len(existing) >= count:
                result[name] = existing
                typer.echo(f"  [{i+1}/{len(playlists)}] {name}: cached ({len(existing)})")
                continue

        if count == 0:
            result[name] = []
            with open(out_file, "w") as f:
                json.dump([], f)
            continue

        all_tracks: list[MelonTrack] = []
        page_size = 50
        start = 1

        typer.echo(f"  [{i+1}/{len(playlists)}] {name}: scraping {count} songs...")

        while start <= count:
            html = _fetch_page(
                f"{BASE}/mymusic/playlist/mymusicplaylistview_listPagingSong.htm",
                {"plylstSeq": seq, "startIndex": str(start), "pageSize": str(page_size)},
            )
            if not html:
                break
            tracks = _parse_songs(html)
            if not tracks:
                break
            all_tracks.extend(tracks)
            start += page_size
            time.sleep(0.3)

        with open(out_file, "w") as f:
            json.dump([vars(t) for t in all_tracks], f, ensure_ascii=False, indent=2)

        result[name] = all_tracks
        typer.echo(f"    Saved {len(all_tracks)} songs")

    return result


def scrape_all(
    member_key: str,
    output_dir: Path,
    likes: bool = True,
    playlists: bool = True,
) -> None:
    """Full scrape: likes + all playlists."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if likes:
        liked = scrape_likes(member_key, output_dir)
        typer.echo(f"Liked songs: {len(liked)}")

    if playlists:
        pl_list = scrape_playlist_list(member_key)
        if pl_list:
            pl_songs = scrape_playlist_songs(member_key, pl_list, output_dir)
            total = sum(len(v) for v in pl_songs.values())
            typer.echo(f"Playlist songs: {total} across {len(pl_songs)} playlists")

    typer.echo("Import complete.")
