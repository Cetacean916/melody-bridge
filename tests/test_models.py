"""Tests for Melody Bridge models."""

from ytmigrate.models import MelonTrack, MatchResult, MatchConfidence, MatchStrategy, Checkpoint


def test_melon_track_creation():
    t = MelonTrack(title="Bohemian Rhapsody", artist="Queen", album="A Night at the Opera")
    assert t.title == "Bohemian Rhapsody"
    assert t.artist == "Queen"
    assert t.album == "A Night at the Opera"


def test_melon_track_default_album():
    t = MelonTrack(title="Test", artist="Artist")
    assert t.album == ""


def test_match_result_not_found():
    t = MelonTrack(title="Unknown", artist="Nobody")
    r = MatchResult(melon=t, not_found=True)
    assert r.not_found is True
    assert r.video_id is None
    assert r.confidence == MatchConfidence.LOW


def test_match_result_found():
    t = MelonTrack(title="Test", artist="A")
    r = MatchResult(
        melon=t,
        video_id="abc123",
        yt_title="Test",
        yt_artist="A",
        confidence=MatchConfidence.HIGH,
        strategy=MatchStrategy.ORIGINAL,
    )
    assert r.video_id == "abc123"
    assert r.confidence == MatchConfidence.HIGH
    assert r.strategy == MatchStrategy.ORIGINAL


def test_checkpoint_defaults():
    cp = Checkpoint(key="test")
    assert cp.total == 0
    assert cp.processed == 0
    assert cp.processed_indices == []
    assert cp.done is False


def test_confidence_values():
    assert MatchConfidence.VERIFIED.value == "verified"
    assert MatchConfidence.HIGH.value == "high"
    assert MatchConfidence.MEDIUM.value == "medium"
    assert MatchConfidence.LOW.value == "low"


def test_strategy_values():
    assert MatchStrategy.ORIGINAL.value == "original_query"
    assert MatchStrategy.PARENS_REMOVED.value == "parens_removed"
    assert MatchStrategy.SHORT_TITLE.value == "short_title"
    assert MatchStrategy.UNFILTERED.value == "unfiltered_fallback"
