"""
tests/simulation_tests/test_lineup.py - Testes para data/lineup.py
"""

import pytest
from src.coachella.data.lineup import (
    get_artist_names,
    get_show,
    get_shows_at_stage,
    get_active_show,
    get_next_show,
    LINEUP,
)


def test_get_artist_names_returns_all():
    names = get_artist_names()
    assert len(names) == len(LINEUP)


def test_get_artist_names_no_duplicates():
    names = get_artist_names()
    assert len(names) == len(set(names))


def test_get_show_existing_artist():
    show = get_show("Bad Bunny")
    assert show is not None
    assert show["stage"] == "Main Stage"
    assert show["start"] == 420
    assert show["duration"] == 60


def test_get_show_nonexistent_artist():
    assert get_show("Taylor Swift") is None


def test_get_shows_at_stage_correct_stage():
    shows = get_shows_at_stage("Main Stage")
    assert all(s["stage"] == "Main Stage" for s in shows)


def test_get_shows_at_stage_ordered():
    shows = get_shows_at_stage("Main Stage")
    starts = [s["start"] for s in shows]
    assert starts == sorted(starts)


def test_get_active_show_during_show():
    # SZA: start=0, duration=40 → ativo entre t=0 e t=40
    show = get_active_show("Outdoor Stage", 10.0)
    assert show is not None
    assert show["artist"] == "Sza"


def test_get_active_show_no_show():
    # Main Stage: primeiro show (Becky G) começa em t=60
    show = get_active_show("Main Stage", 10.0)
    assert show is None


def test_get_active_show_exactly_at_end():
    # t=40 já não é ativo (start=0, duration=40 → [0, 40[)
    show = get_active_show("Outdoor Stage", 40.0)
    assert show is None


def test_get_next_show_returns_correct():
    # Main Stage em t=10: próximo é Becky G (start=60)
    show = get_next_show("Main Stage", 10.0)
    assert show is not None
    assert show["artist"] == "Becky G"


def test_get_next_show_no_more_shows():
    # Main Stage em t=480: já não há mais shows
    show = get_next_show("Main Stage", 480.0)
    assert show is None