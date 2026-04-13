"""Tests for matching engine (unit tests without YTM API)."""

from ytmigrate.matcher import _clean_title, _short_title, _normalize, _artist_matches


def test_clean_title_parens():
    assert _clean_title("Boys And Girls (GIRLS' GENERATION)") == "Boys And Girls"


def test_clean_title_brackets():
    assert _clean_title("Song [Remix]") == "Song"


def test_clean_title_no_parens():
    assert _clean_title("Simple Song") == "Simple Song"


def test_clean_title_nested():
    assert _clean_title("FEVERLOG (Prod.도끼)") == "FEVERLOG"


def test_short_title_with_dash():
    assert _short_title("First Part - Second Part") == "First Part"


def test_short_title_no_dash():
    assert _short_title("Simple") == "Simple"


def test_short_title_en_dash():
    result = _short_title("Part 1 – Part 2")
    assert "Part 1" in result


def test_normalize_spaces():
    assert _normalize("  Hello   World  ") == "hello world"


def test_normalize_case():
    assert _normalize("IU") == "iu"


def test_artist_matches_direct():
    assert _artist_matches("IU", "아이유") is True


def test_artist_matches_variant():
    assert _artist_matches("EPIK HIGH", "에픽하이") is True


def test_artist_matches_no_match():
    assert _artist_matches("BTS", "아이유") is False


def test_artist_matches_substring():
    assert _artist_matches("IU,feat", "아이유") is True
