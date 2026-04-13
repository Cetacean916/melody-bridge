"""YTM authentication: setup, refresh from Firefox cookies, validation."""

import hashlib
import json
import os
import shutil
import sqlite3
import time
from pathlib import Path

import typer
from ytmusicapi import YTMusic

ORIGIN = "https://music.youtube.com"

# Required cookies — if any of these are missing, auth will fail.
REQUIRED_COOKIES = ["__Secure-3PAPISID", "__Secure-1PSIDTS", "SID"]

# All useful cookies to extract.
WANTED_COOKIES = [
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "__Secure-1PSID", "__Secure-3PSID",
    "__Secure-1PSIDTS", "__Secure-3PSIDTS",
    "__Secure-1PAPISID", "__Secure-3PAPISID",
    "__Secure-1PSIDCC", "__Secure-3PSIDCC",
    "LOGIN_INFO", "SIDCC", "PREF", "VISITOR_INFO1_LIVE",
    "__Secure-BUCKET", "YSC", "__Secure-YNID",
    "CONSISTENCY", "__Secure-ROLLOUT_TOKEN",
]


def _auth_path(state_dir: Path) -> Path:
    return state_dir / "headers_auth.json"


def _build_auth_json(cookies: dict[str, str]) -> dict:
    """Build the headers_auth.json structure from extracted cookies."""
    sapisid = cookies["__Secure-3PAPISID"]
    ts = str(int(time.time()))
    h = hashlib.sha1(f"{ts} {sapisid} {ORIGIN}".encode()).hexdigest()
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return {
        "authorization": f"SAPISIDHASH {ts}_{h}",
        "cookie": cookie_str,
        "Origin": ORIGIN,
        "X-Origin": ORIGIN,
        "Referer": f"{ORIGIN}/",
    }


def _find_firefox_profile() -> Path | None:
    """Find the default Firefox profile directory."""
    ff_dir = Path("~/.mozilla/firefox").expanduser()
    if not ff_dir.exists():
        return None
    # Look for .default-release first, then .default
    for suffix in [".default-release", ".default"]:
        matches = list(ff_dir.glob(f"*{suffix}"))
        if matches:
            return matches[0]
    return None


def _extract_cookies_from_firefox(profile: Path) -> dict[str, str] | None:
    """Extract YouTube cookies from Firefox cookies.sqlite."""
    src = profile / "cookies.sqlite"
    if not src.exists():
        return None

    tmp = "/tmp/ytmigrate_ff_cookies.sqlite"
    try:
        shutil.copy2(str(src), tmp)
    except Exception:
        return None

    try:
        db = sqlite3.connect(tmp)
        cur = db.cursor()
        cur.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%youtube.com%'"
        )
        all_cookies = {name: value for name, value in cur.fetchall() if value}
        db.close()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    filtered = {k: v for k, v in all_cookies.items() if k in WANTED_COOKIES}

    for req in REQUIRED_COOKIES:
        if req not in filtered or not filtered[req]:
            typer.echo(f"  Missing required cookie: {req}", err=True)
            return None

    return filtered


def _verify_auth(auth_path: Path) -> YTMusic | None:
    """Verify auth works by creating and deleting a dummy playlist."""
    try:
        yt = YTMusic(str(auth_path))
        pl_id = yt.create_playlist("_ytmigrate_check", "t")
        yt.delete_playlist(pl_id)
        return yt
    except Exception as e:
        typer.echo(f"  Verification failed: {e}", err=True)
        return None


def setup(state_dir: Path) -> None:
    """Guide user through initial auth setup."""
    auth_path = _auth_path(state_dir)

    typer.echo("Melody Bridge — YTM Authentication Setup")
    typer.echo("")

    # Try auto-detect from Firefox first
    profile = _find_firefox_profile()
    if profile:
        typer.echo(f"Found Firefox profile: {profile}")
        typer.echo("Attempting auto-refresh from Firefox cookies...")
        cookies = _extract_cookies_from_firefox(profile)
        if cookies:
            auth_json = _build_auth_json(cookies)
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            with open(auth_path, "w") as f:
                json.dump(auth_json, f, indent=2)
            typer.echo(f"Auth file written to {auth_path}")

            typer.echo("Verifying...")
            yt = _verify_auth(auth_path)
            if yt:
                typer.echo("✓ Auth verified — read and write access OK.")
                return
            typer.echo("✗ Verification failed.", err=True)

    # Manual fallback
    typer.echo("")
    typer.echo("Auto-setup failed. Manual setup:")
    typer.echo("1. Open Firefox, go to music.youtube.com, make sure you're logged in")
    typer.echo("2. Open DevTools (F12) → Network tab")
    typer.echo("3. Browse any song, find a 'browse' request")
    typer.echo("4. Copy the request headers as JSON")
    typer.echo(f"5. Save to: {auth_path}")
    typer.echo("")
    typer.echo("Required keys: authorization, cookie, Origin, X-Origin")


def refresh(state_dir: Path) -> YTMusic | None:
    """Refresh auth from Firefox cookies. Returns YTMusic instance or None."""
    auth_path = _auth_path(state_dir)

    profile = _find_firefox_profile()
    if not profile:
        typer.echo("No Firefox profile found.", err=True)
        return None

    cookies = _extract_cookies_from_firefox(profile)
    if not cookies:
        typer.echo("Failed to extract cookies.", err=True)
        return None

    auth_json = _build_auth_json(cookies)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    with open(auth_path, "w") as f:
        json.dump(auth_json, f, indent=2)

    yt = _verify_auth(auth_path)
    if yt:
        typer.echo(f"✓ Auth refreshed at {time.strftime('%H:%M:%S')}")
        return yt

    typer.echo("✗ Auth refresh failed.", err=True)
    return None


def check(state_dir: Path) -> None:
    """Check if current auth is valid."""
    auth_path = _auth_path(state_dir)
    if not auth_path.exists():
        typer.echo("No auth file found. Run: ytmigrate auth setup")
        raise typer.Exit(1)

    with open(auth_path) as f:
        auth_json = json.load(f)

    # Check required keys
    missing = [k for k in ["Origin", "X-Origin", "cookie", "authorization"]
               if k not in auth_json]
    if missing:
        typer.echo(f"✗ Missing keys: {', '.join(missing)}")
        raise typer.Exit(1)

    typer.echo("Auth file structure OK. Verifying with YTM...")
    yt = _verify_auth(auth_path)
    if yt:
        typer.echo("✓ Auth is valid — read and write access OK.")
    else:
        typer.echo("✗ Auth expired or invalid. Run: ytmigrate auth refresh")
        raise typer.Exit(1)


def get_yt(state_dir: Path) -> YTMusic:
    """Get a YTMusic instance, auto-refreshing if needed."""
    auth_path = _auth_path(state_dir)

    if auth_path.exists():
        yt = _verify_auth(auth_path)
        if yt:
            return yt

    # Try refresh
    yt = refresh(state_dir)
    if yt:
        return yt

    typer.echo("Cannot authenticate. Run: ytmigrate auth setup", err=True)
    raise typer.Exit(1)
