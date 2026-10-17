from pathlib import Path

import pytest
from PIL import Image

from lfdata.importer.tdf import parse_tdf
from lfdata.model import LFGame, PlayerStateHistory
from lfdata.model.constants.tdf import LFPlayerState
from lfdata.video.downtime import (
    DowntimeAnalyzer,
    DowntimeIncident,
    adjust_downtime_asset,
)


def test_downtime_incident_computation() -> None:
    inc = DowntimeIncident(
        entity_id='P1',
        down_time_ms=1000,
        resettable_time_ms=3000,
        up_time_ms=9000,
    )
    assert inc.total_downtime_ms == 8000
    assert inc.time_to_resettable_ms == 2000


def test_downtime_analyzer_empty_game() -> None:
    game = LFGame(game_id='g1')
    analyzer = DowntimeAnalyzer()
    params = analyzer.analyze(game=game)

    assert params.total_downtime_ms == 8000
    assert params.time_to_resettable_ms == 4000
    assert params.resettable_percentage == 0.5
    assert len(params.incidents) == 0


def test_downtime_analyzer_invalid_max_incidents() -> None:
    game = LFGame(game_id='g1')
    analyzer = DowntimeAnalyzer()
    with pytest.raises(ValueError, match='at least 1'):
        analyzer.analyze(game=game, max_incidents=0)


def test_downtime_analyzer_valid_incidents() -> None:
    game = LFGame(game_id='g_test')
    # Player 1 has 2 valid incidents:
    # Incident 1: 0 -> 3 (t=100) -> 2 (t=3100) -> 0 (t=9100)
    #   dt_tot=9000, dt_res=3000
    # Incident 2: 0 -> 3 (t=15000) -> 2 (t=17000) -> 0 (t=22000)
    #   dt_tot=7000, dt_res=2000
    # Player 2 has 1 valid incident:
    # Incident 3: 0 -> 3 (t=500) -> 2 (t=2500) -> 0 (t=8500)
    #   dt_tot=8000, dt_res=2000
    game.state_history = [
        PlayerStateHistory(
            game_id='g_test',
            time=0,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=100,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=3100,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=9100,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=15000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=17000,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=22000,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=0,
            entity_id='P2',
            state=LFPlayerState.UP,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=500,
            entity_id='P2',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=2500,
            entity_id='P2',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_test',
            time=8500,
            entity_id='P2',
            state=LFPlayerState.UP,
        ),
    ]

    analyzer = DowntimeAnalyzer()
    params = analyzer.analyze(game=game, max_incidents=5)

    assert len(params.incidents) == 3
    # Sorted by down_time_ms:
    # 1. P1 @ 100: dt_tot=9000, dt_res=3000
    # 2. P2 @ 500: dt_tot=8000, dt_res=2000
    # 3. P1 @ 15000: dt_tot=7000, dt_res=2000
    assert params.incidents[0].entity_id == 'P1'
    assert params.incidents[0].down_time_ms == 100
    assert params.incidents[1].entity_id == 'P2'
    assert params.incidents[1].down_time_ms == 500
    assert params.incidents[2].entity_id == 'P1'
    assert params.incidents[2].down_time_ms == 15000

    # Averages:
    # Total = (9000 + 8000 + 7000) / 3 = 8000 ms
    # Resettable = (3000 + 2000 + 2000) / 3 = 7000 / 3 = 2333.33 -> 2333 ms
    assert params.total_downtime_ms == 8000
    assert params.time_to_resettable_ms == 2333
    assert pytest.approx(params.resettable_percentage, 0.001) == (
        2333.3333 / 8000
    )


def test_downtime_analyzer_ignores_back_and_forth_and_invalid() -> None:
    game = LFGame(game_id='g_invalid')
    game.state_history = [
        # Sequence 1: 0 -> 3 -> 2 -> 3 -> 2 -> 0 (back and forth, should be ignored)
        PlayerStateHistory(
            game_id='g_invalid',
            time=0,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=1000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=3000,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=4000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=6000,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=9000,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        # Sequence 2: 0 -> 3 -> 0 directly (no resettable, should be ignored)
        PlayerStateHistory(
            game_id='g_invalid',
            time=10000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=18000,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        # Sequence 3: duplicate 3s: 0 -> 3 -> 3 -> 2 -> 0 (should be ignored)
        PlayerStateHistory(
            game_id='g_invalid',
            time=20000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=21000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=24000,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=28000,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
        # Sequence 4: valid incident following the previous returns to UP:
        # 0 -> 3 -> 2 -> 0
        PlayerStateHistory(
            game_id='g_invalid',
            time=30000,
            entity_id='P1',
            state=LFPlayerState.DOWN,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=34000,
            entity_id='P1',
            state=LFPlayerState.RESETTABLE,
        ),
        PlayerStateHistory(
            game_id='g_invalid',
            time=38000,
            entity_id='P1',
            state=LFPlayerState.UP,
        ),
    ]

    analyzer = DowntimeAnalyzer()
    params = analyzer.analyze(game=game)

    assert len(params.incidents) == 1
    assert params.incidents[0].down_time_ms == 30000
    assert params.total_downtime_ms == 8000
    assert params.time_to_resettable_ms == 4000
    assert params.resettable_percentage == 0.5


def test_downtime_analyzer_real_tdf() -> None:
    real_path = Path('assets') / 'sm5_sanitized.tdf'
    if not real_path.exists():
        pytest.skip('sm5_sanitized.tdf not found')

    game = parse_tdf(real_path)
    analyzer = DowntimeAnalyzer()
    params = analyzer.analyze(game=game, max_incidents=5)

    assert len(params.incidents) == 5
    # Standard SM5 is roughly 8000 ms total and 4000 ms resettable
    assert 7900 <= params.total_downtime_ms <= 8200
    assert 3900 <= params.time_to_resettable_ms <= 4200
    assert 0.49 <= params.resettable_percentage <= 0.52


def test_adjust_downtime_asset_no_change() -> None:
    img = Image.new('RGBA', (100, 20), (255, 0, 0, 255))
    # Percentage at 0.5 should return the exact same image
    result = adjust_downtime_asset(
        original_image=img, resettable_percentage=0.5
    )
    assert result is img

    # Difference within default threshold 0.02
    result_near = adjust_downtime_asset(
        original_image=img,
        resettable_percentage=0.51,
    )
    assert result_near is img


def test_adjust_downtime_asset_resized() -> None:
    # Create image with left half RED and right half BLUE
    width, height = 200, 40
    img = Image.new('RGBA', (width, height))
    for x in range(width):
        for y in range(height):
            if x < 100:
                img.putpixel((x, y), (255, 0, 0, 255))
            else:
                img.putpixel((x, y), (0, 0, 255, 255))

    # Adjust to 25% (left half squeezed into left 25%, right stretched to 75%)
    adjusted = adjust_downtime_asset(
        original_image=img,
        resettable_percentage=0.25,
    )
    try:
        assert adjusted is not img
        assert adjusted.size == (width, height)
        # Pixel at x=20 (inside left 25% = 50px) should be predominantly red
        px_left = adjusted.getpixel((20, 20))
        assert px_left[0] > 200 and px_left[2] < 50
        # Pixel at x=80 (inside right 75% = 50px to 200px) should be predominantly blue
        px_right = adjusted.getpixel((80, 20))
        assert px_right[2] > 200 and px_right[0] < 50
    finally:
        adjusted.close()
        img.close()


def test_adjust_downtime_asset_invalid_percentage() -> None:
    img = Image.new('RGBA', (10, 10))
    with pytest.raises(ValueError, match='between 0.0 and 1.0'):
        adjust_downtime_asset(original_image=img, resettable_percentage=-0.1)
    with pytest.raises(ValueError, match='between 0.0 and 1.0'):
        adjust_downtime_asset(original_image=img, resettable_percentage=1.2)
    img.close()
