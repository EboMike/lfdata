from datetime import datetime
from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
from lfdata.video.generator import VisualElementGenerator


def test_visual_element_generator() -> None:
    # 1. Create mock game
    game = LFGame(
        game_id='test_vid_game', timestamp=datetime.now(), game_type='SM5'
    )

    # Teams
    t1 = GameTeam(
        game_id='test_vid_game',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]

    # Entity (Commander on team 0)
    cmd = GameEntity(
        game_id='test_vid_game',
        entity_id='C1',
        type='player',
        desc='Sqnfdcp',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    game.entities = [cmd]

    # E2 downs C1 at 3000 ms
    e2 = GameEntity(
        game_id='test_vid_game',
        entity_id='E2',
        type='player',
        desc='Enemy',
        team_index=1,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities.append(e2)

    events = [
        GameEvent(
            game_id='test_rule_game',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        ),
        GameEvent(
            game_id='test_rule_game',
            time=3000,
            event_type='0206',
            actor_entity_id='E2',
            target_entity_id='C1',
            action='zaps',
            raw_message='',
        ),
    ]
    game.events = events

    hud_gen = VisualElementGenerator(game, 'Sqnfdcp')

    # 1. Generate at 1000 ms (active player)
    elements_active = hud_gen.generate_at(1000)

    types = [el.element_type for el in elements_active]
    assert 'text' in types

    texts = [el.text for el in elements_active if el.text]
    assert 'Game Type: SM5' in texts
    assert 'Sqnfdcp' in texts
    assert 'Commander' in texts
    assert '0' in texts

    counters = {
        el.icon: el for el in elements_active if el.element_type == 'counter'
    }
    assert 'lives' in counters
    assert counters['lives'].current_value == 15
    assert counters['lives'].max_value == 30
    assert 'shots' in counters
    assert counters['shots'].current_value == 30
    assert counters['shots'].max_value == 60
    assert 'missiles' in counters
    assert counters['missiles'].current_value == 5
    assert counters['missiles'].max_value == 5
    assert 'sp' in counters
    assert counters['sp'].current_value == 0
    assert counters['sp'].max_value == 100

    assert not any(el.element_type == 'downtime_bar' for el in elements_active)

    # 2. Generate at 5000 ms (downed player, safe phase)
    elements_down = hud_gen.generate_at(5000)

    bar_el = next(
        (el for el in elements_down if el.element_type == 'downtime_bar'), None
    )
    assert bar_el is not None
    assert bar_el.safe_ms == 2000
    assert bar_el.resettable_ms == 4000


def test_visual_element_generator_new_features() -> None:
    game = LFGame(
        game_id='test_vid_game2',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=4000,
    )
    t1 = GameTeam(
        game_id='test_vid_game2',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id='test_vid_game2',
        entity_id='C1',
        type='player',
        desc='Player1',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    game.entities = [cmd]
    game.events = [
        GameEvent(
            game_id='test_vid_game2',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    hud_gen = VisualElementGenerator(game, 'Player1')

    elements = hud_gen.generate_at(1000)
    texts = [el.text for el in elements if el.text]
    assert '00:01' in texts

    elements_capped = hud_gen.generate_at(5000)
    texts_capped = [el.text for el in elements_capped if el.text]
    assert '00:04' in texts_capped

    sb_el = next(
        (el for el in elements if el.element_type == 'scoreboard'), None
    )
    assert sb_el is not None
    assert sb_el.scoreboard_data is not None
    teams = sb_el.scoreboard_data['teams']
    assert len(teams) == 1
    team_data = teams[0]
    assert team_data['team_name'] == 'Fire Team'
    assert team_data['color_rgb'] == '#FF5000'
    assert len(team_data['players']) == 1
    p_data = team_data['players'][0]
    assert p_data['codename'] == 'Player1'
    assert p_data['role_name'] == 'Commander'
    assert p_data['score'] == 0
    assert p_data['lives'] == 15
    assert p_data['shots'] == 30
    assert p_data['missiles'] == 5
    assert p_data['special_points'] == 0
    assert team_data['totals']['score'] == 0


def test_config_merging() -> None:
    from lfdata.video.generator import _merge_configs, DEFAULT_CONFIG

    custom = {
        'fps': 30,
        'elements': {'game_type': {'enabled': False, 'style': {'size': 12}}},
    }
    merged = _merge_configs(DEFAULT_CONFIG, custom)
    assert merged['fps'] == 30
    assert merged['elements']['game_type']['enabled'] is False
    assert merged['elements']['game_type']['style']['size'] == 12
    # Ensure other elements are preserved
    assert merged['elements']['time']['enabled'] is True


def test_animation_progress_and_fade_alpha() -> None:
    from lfdata.video.generator import apply_animation, get_fade_alpha

    # Linear
    assert apply_animation(0.5, 'linear') == 0.5
    # Ease-in
    assert apply_animation(0.5, 'ease-in') == 0.25
    # Ease-out
    assert apply_animation(0.5, 'ease-out') == 0.75
    # Ease-in-out
    assert apply_animation(0.5, 'ease-in-out') == 0.5
    assert apply_animation(0.25, 'ease-in-out') == 0.15625

    # Fade Alpha
    # linear: 1.0 - 0.5 = 0.5
    assert get_fade_alpha(500, 1000, 'linear') == 0.5
    # ease-in-out: 1.0 - 0.5 = 0.5
    assert get_fade_alpha(500, 1000, 'ease-in-out') == 0.5


def test_scoreboard_visual_rank_transition() -> None:
    from lfdata.video.generator import get_visual_rank

    # transitions: list of (time, start_visual_rank, target_rank)
    trans = [(1000, 1.0, 2), (3000, 2.0, 1)]
    # Before any transition
    assert get_visual_rank(0, 500, trans, 1, 'linear') == 1.0
    # During transition 1 (1000 -> 2000 ms)
    # At 1500 ms (linear progress = 0.5)
    assert get_visual_rank(0, 1500, trans, 1, 'linear') == 1.5
    # After transition 1 (2000 -> 3000 ms)
    assert get_visual_rank(0, 2500, trans, 1, 'linear') == 2.0
    # During transition 2 (3000 -> 4000 ms)
    # At 3250 ms (linear progress = 0.25)
    assert get_visual_rank(0, 3250, trans, 1, 'linear') == 1.75
    # After all transitions
    assert get_visual_rank(0, 5000, trans, 1, 'linear') == 1.0


def test_scoreboard_hp_total_filtering() -> None:
    from lfdata.model import GameTeam, GameEntity, GameEvent
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id='test_hp_filter',
        timestamp=datetime.now(),
        game_type='SM5',
        duration=2000,
    )
    t1 = GameTeam(
        game_id='test_hp_filter',
        team_index=0,
        desc='Fire Team',
        color_enum=11,
        color_desc='Fire',
        color_rgb='#FF5000',
    )
    game.teams = [t1]

    # Commander (max_hp = 3)
    p1 = GameEntity(
        game_id='test_hp_filter',
        entity_id='P1',
        type='player',
        desc='Cmdr',
        team_index=0,
        level=1,
        category=1,
        battlesuit='Maverick',
    )
    # Scout (max_hp = 1)
    p2 = GameEntity(
        game_id='test_hp_filter',
        entity_id='P2',
        type='player',
        desc='Sct',
        team_index=0,
        level=1,
        category=3,
        battlesuit='Interceptor',
    )
    game.entities = [p1, p2]
    game.events = [
        GameEvent(
            game_id='test_hp_filter',
            time=0,
            event_type='0100',
            action='start',
            raw_message='',
        )
    ]

    hud_gen = VisualElementGenerator(game, 'Cmdr')
    elements = hud_gen.generate_at(1000)
    sb_el = next(
        (el for el in elements if el.element_type == 'scoreboard'), None
    )
    assert sb_el is not None
    teams = sb_el.scoreboard_data['teams']
    team_data = teams[0]

    # Assert player HP details in data dictionary
    p1_data = next(d for d in team_data['players'] if d['codename'] == 'Cmdr')
    p2_data = next(d for d in team_data['players'] if d['codename'] == 'Sct')
    assert p1_data['hp'] == 3
    assert p2_data['hp'] == 1

    # Total HP should only sum Commander (3), not Scout (1), so total is 3
    assert team_data['totals']['hp'] == 3
