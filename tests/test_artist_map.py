"""Tests for artist mapping."""

from ytmigrate.artist_map import get_search_variants, canonical_name, ARTIST_MAP


def test_get_search_variants_known():
    variants = get_search_variants("아이유")
    assert "아이유" in variants
    assert "IU" in variants


def test_get_search_variants_unknown():
    variants = get_search_variants("UnknownArtist")
    assert variants == ["UnknownArtist"]


def test_get_search_variants_japanese():
    variants = get_search_variants("藤田恵美")
    assert "Emi Fujita" in variants


def test_canonical_name_from_english():
    assert canonical_name("IU") == "아이유"
    assert canonical_name("iu") == "아이유"


def test_canonical_name_from_korean():
    assert canonical_name("아이유") == "아이유"


def test_canonical_name_not_found():
    assert canonical_name("TotallyUnknown") is None


def test_artist_map_has_entries():
    assert len(ARTIST_MAP) >= 30


def test_canonical_name_japanese():
    assert canonical_name("Emi Fujita") == "藤田恵美"
    assert canonical_name("Nakashima Mika") == "中島美嘉"
