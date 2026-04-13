"""Data models for Melody Bridge."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MatchConfidence(Enum):
    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchStrategy(Enum):
    ORIGINAL = "original_query"
    PARENS_REMOVED = "parens_removed"
    SHORT_TITLE = "short_title"
    ARTIST_MAPPED = "artist_mapped"
    UNFILTERED = "unfiltered_fallback"


@dataclass
class MelonTrack:
    title: str
    artist: str
    album: str = ""


@dataclass
class MatchResult:
    melon: MelonTrack
    video_id: Optional[str] = None
    yt_title: str = ""
    yt_artist: str = ""
    confidence: MatchConfidence = MatchConfidence.LOW
    strategy: MatchStrategy = MatchStrategy.ORIGINAL
    not_found: bool = False


@dataclass
class Checkpoint:
    key: str
    total: int = 0
    processed: int = 0
    matched: int = 0
    not_found: int = 0
    done: bool = False
    processed_indices: list[int] = field(default_factory=list)
    not_found_items: list[str] = field(default_factory=list)
    playlist_id: str = ""
