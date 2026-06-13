from datetime import datetime
from lfdata.model import LFGame, GameTeam, GameEntity, GameEvent
from lfdata.video.generator import (
    VisualElementGenerator,
    LFNukeInterval,
    LFTeamTransition,
)
from lfdata.video.element import (
    LFEventLogEntry,
    LFPlayerEventLogEntry,
)


def test_visual_element_generator() -> None:
    # 1. Create mock game
    game = LFGame(game_id="test_vid_game", timestamp=datetime.now(), game_type="SM5")

    # Teams
    t1 = GameTeam(
        game_id="test_vid_game",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    game.teams = [t1]

    # Entity (Commander on team 0)
    cmd = GameEntity(
        game_id="test_vid_game",
        entity_id="C1",
        type="player",
        desc="Sqnfdcp",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [cmd]

    # E2 downs C1 at 3000 ms
    e2 = GameEntity(
        game_id="test_vid_game",
        entity_id="E2",
        type="player",
        desc="Enemy",
        team_index=1,
        level=1,
        category=3,
        battlesuit="Interceptor",
    )
    game.entities.append(e2)

    events = [
        GameEvent(
            game_id="test_rule_game",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        ),
        GameEvent(
            game_id="test_rule_game",
            time=3000,
            event_type="0206",
            actor_entity_id="E2",
            target_entity_id="C1",
            action="zaps",
            raw_message="",
        ),
    ]
    game.events = events

    hud_gen = VisualElementGenerator(game, "Sqnfdcp")

    # 1. Generate at 1000 ms (active player)
    elements_active = hud_gen.generate_at(1000)

    types = [el.element_type for el in elements_active]
    assert "text" in types

    texts = [el.text for el in elements_active if el.text]
    assert "Game Type: SM5" in texts
    assert "Sqnfdcp" in texts
    assert "Commander" in texts
    assert "0" in texts

    counters = {el.icon: el for el in elements_active if el.element_type == "counter"}
    assert "lives" in counters
    assert counters["lives"].current_value == 15
    assert counters["lives"].max_value == 30
    assert "shots" in counters
    assert counters["shots"].current_value == 30
    assert counters["shots"].max_value == 60
    assert "missiles" in counters
    assert counters["missiles"].current_value == 5
    assert counters["missiles"].max_value == 5
    assert "sp" in counters
    assert counters["sp"].current_value == 0
    assert counters["sp"].max_value == 99

    assert not any(el.element_type == "downtime_bar" for el in elements_active)

    # 2. Generate at 5000 ms (downed player, safe phase)
    elements_down = hud_gen.generate_at(5000)

    bar_el = next(
        (el for el in elements_down if el.element_type == "downtime_bar"), None
    )
    assert bar_el is not None
    assert bar_el.safe_ms == 2000
    assert bar_el.resettable_ms == 4000


def test_visual_element_generator_new_features() -> None:
    game = LFGame(
        game_id="test_vid_game2",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=4000,
    )
    t1 = GameTeam(
        game_id="test_vid_game2",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    game.teams = [t1]
    cmd = GameEntity(
        game_id="test_vid_game2",
        entity_id="C1",
        type="player",
        desc="Player1",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [cmd]
    game.events = [
        GameEvent(
            game_id="test_vid_game2",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        )
    ]

    hud_gen = VisualElementGenerator(game, "Player1")

    elements = hud_gen.generate_at(1000)
    texts = [el.text for el in elements if el.text]
    assert "00:01" in texts

    elements_capped = hud_gen.generate_at(5000)
    texts_capped = [el.text for el in elements_capped if el.text]
    assert "00:04" in texts_capped

    sb_el = next((el for el in elements if el.element_type == "scoreboard"), None)
    assert sb_el is not None
    assert sb_el.scoreboard_data is not None
    teams = sb_el.scoreboard_data.teams
    assert len(teams) == 1
    team_data = teams[0]
    assert team_data.team_name == "Fire Team"
    assert team_data.color_rgb == "#FF5000"
    assert len(team_data.players) == 1
    p_data = team_data.players[0]
    assert p_data.codename == "Player1"
    assert p_data.role_name == "Commander"
    assert p_data.score == 0
    assert p_data.lives == 15
    assert p_data.shots == 30
    assert p_data.missiles == 5
    assert p_data.special_points == 0
    assert team_data.totals.score == 0


def test_generator_heavy_no_special_points() -> None:
    game = LFGame(
        game_id="test_heavy_sp_generator",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    t1 = GameTeam(
        game_id="test_heavy_sp_generator",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    game.teams = [t1]
    heavy = GameEntity(
        game_id="test_heavy_sp_generator",
        entity_id="H1",
        type="player",
        desc="HeavyPlayer",
        team_index=0,
        level=1,
        category=2,  # Heavy
        battlesuit="Titan",
    )
    game.entities = [heavy]
    game.events = [
        GameEvent(
            game_id="test_heavy_sp_generator",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        )
    ]

    hud_gen = VisualElementGenerator(game, "HeavyPlayer")
    elements = hud_gen.generate_at(1000)

    counters = {el.icon: el for el in elements if el.element_type == "counter"}
    assert "sp" not in counters


def test_config_merging() -> None:

    from lfdata.video.generator import _merge_configs, DEFAULT_CONFIG

    custom = {
        "fps": 30,
        "elements": {"game_type": {"enabled": False, "style": {"size": 12}}},
    }
    merged = _merge_configs(DEFAULT_CONFIG, custom)
    assert merged["fps"] == 30
    assert merged["elements"]["game_type"]["enabled"] is False
    assert merged["elements"]["game_type"]["style"]["size"] == 12
    # Ensure other elements are preserved
    assert merged["elements"]["time"]["enabled"] is True


def test_animation_progress_and_fade_alpha() -> None:
    from lfdata.video.generator import apply_animation, get_fade_alpha

    # Linear
    assert apply_animation(0.5, "linear") == 0.5
    # Ease-in
    assert apply_animation(0.5, "ease-in") == 0.25
    # Ease-out
    assert apply_animation(0.5, "ease-out") == 0.75
    # Ease-in-out
    assert apply_animation(0.5, "ease-in-out") == 0.5
    assert apply_animation(0.25, "ease-in-out") == 0.15625

    # Fade Alpha
    # linear: 1.0 - 0.5 = 0.5
    assert get_fade_alpha(500, 1000, "linear") == 0.5
    # ease-in-out: 1.0 - 0.5 = 0.5
    assert get_fade_alpha(500, 1000, "ease-in-out") == 0.5


def test_scoreboard_visual_rank_transition() -> None:
    from lfdata.video.generator import get_visual_rank

    trans = [
        LFTeamTransition(event_time_ms=1000, visual_rank=1.0, ranking=2),
        LFTeamTransition(event_time_ms=3000, visual_rank=2.0, ranking=1),
    ]
    # Before any transition
    assert get_visual_rank(0, 500, trans, 1, "linear") == 1.0
    # During transition 1 (1000 -> 2000 ms)
    # At 1500 ms (linear progress = 0.5)
    assert get_visual_rank(0, 1500, trans, 1, "linear") == 1.5
    # After transition 1 (2000 -> 3000 ms)
    assert get_visual_rank(0, 2500, trans, 1, "linear") == 2.0
    # During transition 2 (3000 -> 4000 ms)
    # At 3250 ms (linear progress = 0.25)
    assert get_visual_rank(0, 3250, trans, 1, "linear") == 1.75
    # After all transitions
    assert get_visual_rank(0, 5000, trans, 1, "linear") == 1.0


def test_scoreboard_hp_total_filtering() -> None:
    from lfdata.model import GameTeam, GameEntity, GameEvent
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id="test_hp_filter",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=2000,
    )
    t1 = GameTeam(
        game_id="test_hp_filter",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    game.teams = [t1]

    # Commander (max_hp = 3)
    p1 = GameEntity(
        game_id="test_hp_filter",
        entity_id="P1",
        type="player",
        desc="Cmdr",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    # Scout (max_hp = 1)
    p2 = GameEntity(
        game_id="test_hp_filter",
        entity_id="P2",
        type="player",
        desc="Sct",
        team_index=0,
        level=1,
        category=3,
        battlesuit="Interceptor",
    )
    game.entities = [p1, p2]
    game.events = [
        GameEvent(
            game_id="test_hp_filter",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        )
    ]

    hud_gen = VisualElementGenerator(game, "Cmdr")
    elements = hud_gen.generate_at(1000)
    sb_el = next((el for el in elements if el.element_type == "scoreboard"), None)
    assert sb_el is not None
    teams = sb_el.scoreboard_data.teams
    team_data = teams[0]

    # Assert player HP details in data dictionary
    p1_data = next(d for d in team_data.players if d.codename == "Cmdr")
    p2_data = next(d for d in team_data.players if d.codename == "Sct")
    assert p1_data.hp == 3
    assert p2_data.hp == 1
    assert p1_data.penalties == 0
    assert p2_data.penalties == 0

    # Total HP should only sum Commander (3), not Scout (1), so total is 3
    assert team_data.totals.hp == 3


def test_event_scroller_miss_filtering() -> None:
    from lfdata.model import GameTeam, GameEntity, GameEvent
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id="test_scroller_miss",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=5000,
    )
    t1 = GameTeam(
        game_id="test_scroller_miss",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    game.teams = [t1]

    p1 = GameEntity(
        game_id="test_scroller_miss",
        entity_id="P1",
        type="player",
        desc="Player1",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    p2 = GameEntity(
        game_id="test_scroller_miss",
        entity_id="P2",
        type="player",
        desc="Player2",
        team_index=0,
        level=1,
        category=3,
        battlesuit="Interceptor",
    )
    game.entities = [p1, p2]

    # Miss event and Zap event
    game.events = [
        GameEvent(
            game_id="test_scroller_miss",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        ),
        GameEvent(
            game_id="test_scroller_miss",
            time=1000,
            event_type="0201",
            actor_entity_id="P1",
            action="miss",
            raw_message="",
        ),
        GameEvent(
            game_id="test_scroller_miss",
            time=2000,
            event_type="0203",
            actor_entity_id="P1",
            target_entity_id="P2",
            action="zap",
            raw_message="",
        ),
    ]

    hud_gen = VisualElementGenerator(game, "Player1")
    elements = hud_gen.generate_at(3000)

    scroller_el = next(
        (el for el in elements if el.element_type == "event_scroller"), None
    )
    assert scroller_el is not None
    events = scroller_el.events_data
    assert events is not None
    # Convert event descriptions to check
    descriptions = [ev.desc for ev in events]

    # Assert that start and zap events are logged, but miss event is not
    assert "* Mission Start *" in descriptions
    assert "Player1 zaps Player2" in descriptions
    assert not any("misses" in desc for desc in descriptions)


def test_important_events_filtering() -> None:
    game = LFGame(
        game_id="test_important_filter",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )
    t0 = GameTeam(
        game_id="test_important_filter",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_desc="Fire",
        color_rgb="#FF5000",
    )
    t1 = GameTeam(
        game_id="test_important_filter",
        team_index=1,
        desc="Earth Team",
        color_enum=12,
        color_desc="Earth",
        color_rgb="#00FF00",
    )
    game.teams = [t0, t1]

    # Medic player on Team 0
    medic = GameEntity(
        game_id="test_important_filter",
        entity_id="M0",
        type="player",
        desc="MedicPlayer",
        team_index=0,
        level=1,
        category=5,
        battlesuit="Maverick",
    )
    # Opponent player
    enemy = GameEntity(
        game_id="test_important_filter",
        entity_id="E1",
        type="player",
        desc="EnemyPlayer",
        team_index=1,
        level=1,
        category=3,
        battlesuit="Maverick",
    )
    game.entities = [medic, enemy]

    # Create a list of events to test:
    # 1. 0100 Mission Start (is_important = False)
    # 2. 0204 Base Destroy by Zap (is_important = False)
    # 3. 0303 Base Destroy by Missile (is_important = False)
    # 4. 0B03 Target Award (is_important = False)
    # 5. 0404 Nuke Activate (is_important = True)
    # 6. 0405 Nuke Detonate (is_important = True)
    events = [
        GameEvent(
            game_id="test_important_filter",
            time=0,
            event_type="0100",
            action="start",
            raw_message="",
        ),
        # Base zap
        GameEvent(
            game_id="test_important_filter",
            time=1000,
            event_type="0204",
            actor_entity_id="E1",
            target_entity_id="B0",
            action="base_destroy",
            raw_message="",
        ),
        # Base missile
        GameEvent(
            game_id="test_important_filter",
            time=1500,
            event_type="0303",
            actor_entity_id="E1",
            target_entity_id="B0",
            action="base_destroy_missile",
            raw_message="",
        ),
        # Target award
        GameEvent(
            game_id="test_important_filter",
            time=1800,
            event_type="0B03",
            actor_entity_id="E1",
            target_entity_id="B0",
            action="target_award",
            raw_message="",
        ),
        # Nuke activate
        GameEvent(
            game_id="test_important_filter",
            time=2000,
            event_type="0404",
            actor_entity_id="E1",
            action="nuke_activate",
            raw_message="",
        ),
        # Nuke detonate
        GameEvent(
            game_id="test_important_filter",
            time=3000,
            event_type="0405",
            actor_entity_id="E1",
            action="nuke_detonate",
            raw_message="",
        ),
    ]

    # Spaced zaps:
    # 17 zaps are needed to reduce lives from 17 to 0.
    # Spacing of 9000 ms starting from 12000 ms.
    for i in range(17):
        events.append(
            GameEvent(
                game_id="test_important_filter",
                time=12000 + i * 9000,
                event_type="0206",
                actor_entity_id="E1",
                target_entity_id="M0",
                action="zap",
                raw_message="",
            )
        )

    game.events = events

    hud_gen = VisualElementGenerator(game, "MedicPlayer")
    # Generate at 180000 ms so all events are processed
    hud_gen.generate_at(180000)

    # Assert importance based on time
    time_to_importance = {ev.time: ev.is_important for ev in hud_gen.event_log}

    # Verify that:
    # time 0 (Mission Start) -> False
    assert time_to_importance[0] is False
    # time 1000 (Base destroy by zap) -> False
    assert time_to_importance[1000] is False
    # time 1500 (Base destroy by missile) -> False
    assert time_to_importance[1500] is False
    # time 1800 (Target award) -> False
    assert time_to_importance[1800] is False
    # time 2000 (Nuke activate) -> True
    assert time_to_importance[2000] is True
    # time 3000 (Nuke detonate) -> True
    assert time_to_importance[3000] is True

    # Check for medic lives checkpoint event (divisible by 5) at 21000 ms
    assert time_to_importance[21000] is True
    medic_events = [ev for ev in hud_gen.event_log if ev.time == 21000]
    medic_event = next((ev for ev in medic_events if ev.desc.startswith("Medic")), None)
    assert medic_event is not None
    assert medic_event.desc == "Medic MedicPlayer has 15 lives left"
    assert medic_event.is_important is True

    # Check for player elimination event at 156000 ms
    assert time_to_importance[156000] is True

    # Check that Team Elimination (which happens at 156000 ms) is NOT important
    events_at_156000 = [ev for ev in hud_gen.event_log if ev.time == 156000]
    team_elim_event = next(
        (ev for ev in events_at_156000 if "Team Fire Team Eliminated" in ev.desc),
        None,
    )
    assert team_elim_event is not None
    assert team_elim_event.is_important is False


def test_camera_shake_triggering() -> None:
    game = LFGame(
        game_id="test_shake_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )
    t0 = GameTeam(
        game_id="test_shake_game",
        team_index=0,
        desc="Fire Team",
        color_enum=11,
        color_rgb="#FF5000",
    )
    t1 = GameTeam(
        game_id="test_shake_game",
        team_index=1,
        desc="Earth Team",
        color_enum=12,
        color_desc="Earth",
        color_rgb="#00FF00",
    )
    game.teams = [t0, t1]

    medic = GameEntity(
        game_id="test_shake_game",
        entity_id="M0",
        type="player",
        desc="MedicPlayer",
        team_index=0,
        level=1,
        category=5,
        battlesuit="Maverick",
    )
    enemy_cmd = GameEntity(
        game_id="test_shake_game",
        entity_id="E1",
        type="player",
        desc="EnemyCommander",
        team_index=1,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [medic, enemy_cmd]

    game.events = [
        GameEvent(
            game_id="test_shake_game",
            time=1000,
            event_type="0306",
            actor_entity_id="E1",
            target_entity_id="M0",
            action="missile",
            raw_message="",
        ),
        GameEvent(
            game_id="test_shake_game",
            time=3000,
            event_type="0405",
            actor_entity_id="E1",
            action="nuke_detonate",
            raw_message="",
        ),
    ]

    hud_gen = VisualElementGenerator(game, "MedicPlayer")

    # Verify camera shakes were precomputed
    assert len(hud_gen.camera_shakes) == 2

    shake1 = hud_gen.camera_shakes[0]
    assert shake1.start_ms == 1000
    assert shake1.duration_ms == 500
    assert shake1.strength == 0.01

    shake2 = hud_gen.camera_shakes[1]
    assert shake2.start_ms == 3000
    assert shake2.duration_ms == 1000
    assert shake2.strength == 0.03

    # Generate at 1250 ms (middle of shake 1: strength should be 0.005)
    elements = hud_gen.generate_at(1250)

    # Let's find game_type and player_name elements
    el_gt = next(
        (
            el
            for el in elements
            if el.element_type == "text" and el.text and "Game Type" in el.text
        ),
        None,
    )
    el_pn = next(
        (
            el
            for el in elements
            if el.element_type == "text" and el.text == "MedicPlayer"
        ),
        None,
    )
    assert el_gt is not None
    assert el_pn is not None

    # Default positions:
    # game_type: x=0.98, y=0.96
    # player_name: x=0.5, y=0.05
    dx_gt = el_gt.x - 0.98
    dy_gt = el_gt.y - 0.96

    dx_pn = el_pn.x - 0.5
    dy_pn = el_pn.y - 0.05

    # Shakes should apply identical offsets
    assert abs(dx_gt - dx_pn) < 1e-7
    assert abs(dy_gt - dy_pn) < 1e-7

    # Offsets should be within the strength bound of 0.005 (at 1250 ms)
    assert abs(dx_gt) <= 0.005 + 1e-7
    assert abs(dy_gt) <= 0.005 + 1e-7

    # Verify that at 1600 ms (after shake 1 ends), the offset is exactly 0
    elements_idle = hud_gen.generate_at(1600)
    el_gt_idle = next(
        (
            el
            for el in elements_idle
            if el.element_type == "text" and el.text and "Game Type" in el.text
        ),
        None,
    )
    assert el_gt_idle is not None
    assert abs(el_gt_idle.x - 0.98) < 1e-7
    assert abs(el_gt_idle.y - 0.96) < 1e-7


def test_multiline_text_slot_allocation() -> None:
    from lfdata.model import LFGame
    from lfdata.video import VisualElementGenerator

    # 1. Create a game with team and entities
    game = LFGame(
        game_id="test_multiline_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=15000,
    )
    hud_gen = VisualElementGenerator(game, "Player1")

    # Directly populate player_event_log to test simulation behavior
    hud_gen.player_event_log = [
        LFPlayerEventLogEntry(time=1000, desc="event 1"),  # Expires at 4000
        LFPlayerEventLogEntry(time=3000, desc="event 2"),  # Expires at 6000
        LFPlayerEventLogEntry(time=5000, desc="event 3"),  # Expires at 8000
        LFPlayerEventLogEntry(time=7000, desc="event 4"),  # Expires at 10000
    ]

    # Test slot allocation logic at different times:
    # At t=2000: event 1 should be in Slot 0, others None
    slots_2000 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.player_event_log,
        time_ms=2000,
        fade_time_ms=3000,
    )
    assert slots_2000[0] is not None and slots_2000[0].text == "event 1"
    assert slots_2000[1] is None
    assert slots_2000[2] is None

    # At t=3500: event 1 is active in Slot 0, event 2 in Slot 1
    slots_3500 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.player_event_log,
        time_ms=3500,
        fade_time_ms=3000,
    )
    assert slots_3500[0] is not None and slots_3500[0].text == "event 1"
    assert slots_3500[1] is not None and slots_3500[1].text == "event 2"
    assert slots_3500[2] is None

    # At t=5500: event 2 active in Slot 1, event 3 goes to Slot 0
    slots_5500 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.player_event_log,
        time_ms=5500,
        fade_time_ms=3000,
    )
    assert slots_5500[0] is not None and slots_5500[0].text == "event 3"
    assert slots_5500[1] is not None and slots_5500[1].text == "event 2"
    assert slots_5500[2] is None

    # At t=7500: event 3 in Slot 0, event 4 goes to Slot 1
    slots_7500 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.player_event_log,
        time_ms=7500,
        fade_time_ms=3000,
    )
    assert slots_7500[0] is not None and slots_7500[0].text == "event 3"
    assert slots_7500[1] is not None and slots_7500[1].text == "event 4"
    assert slots_7500[2] is None

    # 2. Test nuke dynamic durations
    # Nuke activates at 2000, cancels/detonates at 8000
    hud_gen.nuke_intervals = [
        LFNukeInterval(start_ms=2000, end_ms=8000, nuker_name="CommanderA"),
    ]
    hud_gen.event_log = [
        LFEventLogEntry(
            time=2000,
            desc="CommanderA activates nuke",
            is_important=True,
        ),
        LFEventLogEntry(
            time=8000,
            desc="CommanderA detonates nuke",
            is_important=True,
        ),
    ]

    # At t=5000: 'activates nuke' should be in Slot 0, duration is 6000 ms
    slots_5000 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.event_log,
        time_ms=5000,
        fade_time_ms=5000,
        is_game_events=True,
    )
    assert slots_5000[0] is not None
    assert "activates nuke" in slots_5000[0].text
    assert slots_5000[0].duration == 6000
    assert slots_5000[0].is_nuke_act is True

    # At t=9000: 'activates nuke' expired, 'detonates nuke' active in Slot 0
    slots_9000 = hud_gen._get_active_multiline_lines(
        event_list=hud_gen.event_log,
        time_ms=9000,
        fade_time_ms=5000,
        is_game_events=True,
    )
    assert slots_9000[0] is not None
    assert "detonates nuke" in slots_9000[0].text
    assert slots_9000[0].duration == 5000
    assert slots_9000[0].is_nuke_act is False

    # 3. Test multi-line text vertical offsets on UIElement list
    game.teams = []
    game.entities = []
    hud_gen.entity_id = "P1"
    hud_gen.player_event_log = [
        LFPlayerEventLogEntry(time=1000, desc="event 1"),
        LFPlayerEventLogEntry(time=2000, desc="event 2"),
    ]
    hud_gen._get_state_at = lambda t: ({}, {})

    elements = hud_gen.generate_at(2500)
    pe_elements = [
        el
        for el in elements
        if el.element_type == "text" and el.text in ("event 1", "event 2")
    ]
    assert len(pe_elements) == 2

    pe1 = next(el for el in pe_elements if el.text == "event 1")
    pe2 = next(el for el in pe_elements if el.text == "event 2")

    # default player_events y = 0.18, font size = 18.
    # line_height = (18 * 1.3) / 800 = 0.02925
    assert abs(pe1.y - 0.18) < 1e-7
    assert abs(pe2.y - 0.20925) < 1e-7


def test_indicator_interval_configuration() -> None:
    """Verifies parsing of indicator interval from config and default rules."""
    from datetime import datetime
    from lfdata.model import LFGame, LFRole
    from lfdata.video import VisualElementGenerator
    from lfdata.replay.state import LFReplayPlayerState

    game = LFGame(
        game_id="test_indicator_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    # 1. Test helper parsing
    gen = VisualElementGenerator(game, "Player1")
    assert gen._parse_indicator_interval(20) == 20
    assert gen._parse_indicator_interval("every 20") == 20
    assert gen._parse_indicator_interval("every 15") == 15
    assert gen._parse_indicator_interval("None") is None
    assert gen._parse_indicator_interval("none") is None
    assert gen._parse_indicator_interval(None) is None
    assert gen._parse_indicator_interval(0) is None
    assert gen._parse_indicator_interval(-5) is None

    # 2. Test default rules for role-based counters
    p_state = LFReplayPlayerState("P1", LFRole.COMMANDER, 0)
    elements = []
    gen._add_player_stats_hud_elements(elements, p_state)
    counters = {el.icon: el for el in elements if el.element_type == "counter"}
    assert counters["missiles"].indicator_interval == 1
    assert counters["shields"].indicator_interval == 1
    assert counters["sp"].indicator_interval == 20

    # Medic
    p_medic = LFReplayPlayerState("P2", LFRole.MEDIC, 0)
    elements_med = []
    gen._add_player_stats_hud_elements(elements_med, p_medic)
    counters_med = {el.icon: el for el in elements_med if el.element_type == "counter"}
    assert counters_med["sp"].indicator_interval == 10

    # Scout
    p_scout = LFReplayPlayerState("P3", LFRole.SCOUT, 0)
    elements_sct = []
    gen._add_player_stats_hud_elements(elements_sct, p_scout)
    counters_sct = {el.icon: el for el in elements_sct if el.element_type == "counter"}
    assert counters_sct["sp"].indicator_interval == 15

    # 3. Test configuration overrides
    gen_override = VisualElementGenerator(
        game,
        "Player1",
        config={
            "elements": {
                "player_special_points": {"indicator_interval": 5},
                "player_missiles": {"indicator_interval": "every 2"},
            }
        },
    )
    elements_over = []
    gen_override._add_player_stats_hud_elements(elements_over, p_state)
    counters_over = {
        el.icon: el for el in elements_over if el.element_type == "counter"
    }
    assert counters_over["sp"].indicator_interval == 5
    assert counters_over["missiles"].indicator_interval == 2


def test_double_resupply_in_place_replacement() -> None:
    """Verifies that a double resupply replaces the previous resupply event."""
    from datetime import datetime
    from lfdata.model import LFGame, GameEvent
    from lfdata.video import VisualElementGenerator

    game = LFGame(
        game_id="test_double_resup_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    gen = VisualElementGenerator(game, "Player1")
    gen.entity_id = "P1"
    gen.entity_names = {"P1": "Player1", "A1": "AmmoX", "M1": "MedicY"}
    from unittest.mock import MagicMock

    mock_replay = MagicMock()
    mock_replay.game_state.players = {}
    mock_replay.game_state.teams = {}

    # Bypass snapshots early exit
    gen.snapshots = [(0, {}, {}), (0, {}, {})]

    # 1. Simulate single ammo resupply at 1000ms
    ev1 = GameEvent(
        game_id="test_double_resup_game",
        time=1000,
        event_type="0500",
        actor_entity_id="A1",
        target_entity_id="P1",
    )
    gen._process_hud_event_triggers(ev1, mock_replay, "")

    assert len(gen.player_event_log) == 1
    assert gen.player_event_log[0].desc == "Resupplied shots by AmmoX"
    assert gen.player_event_log[0].time == 1000

    # 2. Simulate medic resupply at 1500ms (within 1000ms, triggering double-resupply)
    ev2 = GameEvent(
        game_id="test_double_resup_game",
        time=1500,
        event_type="0502",
        actor_entity_id="M1",
        target_entity_id="P1",
    )
    gen._process_hud_event_triggers(ev2, mock_replay, "")

    # Verifies that it replaced in-place and NO new event was appended
    assert len(gen.player_event_log) == 1
    event_entry = gen.player_event_log[0]
    assert event_entry.time == 1000
    assert event_entry.desc == "Resupplied shots by AmmoX"
    assert event_entry.double_resup_desc == "Double-resupply by AmmoX and MedicY"
    assert event_entry.double_resup_time == 1500

    # 3. Verify multiline slot allocation resolves correctly at different times
    # At t = 1200ms: should show original single resupply text
    slots_1200 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=1200,
        fade_time_ms=3000,
    )
    assert slots_1200[0] is not None
    assert slots_1200[0].text == "Resupplied shots by AmmoX"

    # At t = 1600ms: should show double resupply text
    slots_1600 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=1600,
        fade_time_ms=3000,
    )
    assert slots_1600[0] is not None
    assert slots_1600[0].text == "Double-resupply by AmmoX and MedicY"


def test_new_ui_elements_and_custom_fields() -> None:
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    # 1. Create a game with a known timestamp
    dt = datetime(2024, 1, 14, 20, 57, 10)
    game = LFGame(
        game_id="test_ui_game",
        timestamp=dt,
        game_type="SM5",
        start="20240114205710",
        centre="4-43",
        arena_name="Invasion",
    )

    # 2. Test default settings (date_of_game enabled, user defined disabled)
    hud_gen = VisualElementGenerator(game, None)
    elements = hud_gen.generate_at(1000)

    # Ensure date_of_game is in elements, and formatted with default format
    date_el = next(
        (
            el
            for el in elements
            if el.element_type == "text" and el.text and "1/14/24" in el.text
        ),
        None,
    )
    assert date_el is not None
    assert date_el.align == "right"
    assert date_el.x == 0.98
    assert date_el.y == 0.92
    assert date_el.style.size == 18

    # Ensure user defined texts are not in elements by default
    user1_el = next((el for el in elements if el.text == "Custom Banner 1"), None)
    assert user1_el is None
    user2_el = next((el for el in elements if el.text == "Custom Banner 2"), None)
    assert user2_el is None
    centre_el = next((el for el in elements if el.text == "Invasion"), None)
    assert centre_el is None

    # 3. Test config overrides: custom format for date, and enable user texts
    config = {
        "elements": {
            "date_of_game": {
                "format": "%Y/%m/%d",
            },
            "user_defined_text_1": {
                "enabled": True,
                "text": "Custom Banner 1",
            },
            "user_defined_text_2": {
                "enabled": True,
                "text": "Custom Banner 2",
            },
            "centre_name": {
                "enabled": True,
            },
        }
    }
    hud_gen_override = VisualElementGenerator(game, None, config=config)
    elements_over = hud_gen_override.generate_at(1000)

    # Check custom format date
    date_el_over = next(
        (
            el
            for el in elements_over
            if el.element_type == "text" and el.text == "2024/01/14"
        ),
        None,
    )
    assert date_el_over is not None

    # Check user defined text 1
    user1_el_over = next(
        (
            el
            for el in elements_over
            if el.element_type == "text" and el.text == "Custom Banner 1"
        ),
        None,
    )
    assert user1_el_over is not None
    assert user1_el_over.align == "left"
    assert user1_el_over.x == 0.1
    assert user1_el_over.y == 0.6
    assert user1_el_over.style.size == 20

    # Check user defined text 2
    user2_el_over = next(
        (
            el
            for el in elements_over
            if el.element_type == "text" and el.text == "Custom Banner 2"
        ),
        None,
    )
    assert user2_el_over is not None
    assert user2_el_over.align == "left"
    assert user2_el_over.x == 0.1
    assert user2_el_over.y == 0.7
    assert user2_el_over.style.size == 20

    # Check centre name
    centre_el_over = next(
        (
            el
            for el in elements_over
            if el.element_type == "text" and el.text == "Invasion"
        ),
        None,
    )
    assert centre_el_over is not None
    assert centre_el_over.align == "left"
    assert centre_el_over.x == 0.1
    assert centre_el_over.y == 0.8
    assert centre_el_over.style.size == 20


def test_player_name_normalization_matching() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameEntity
    from lfdata.video import VisualElementGenerator

    game = LFGame(
        game_id="test_norm_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    p = GameEntity(
        game_id="test_norm_game",
        entity_id="P123",
        type="player",
        desc=" anchovy!",
        team_index=0,
        level=1,
        category=1,
        battlesuit="Maverick",
    )
    game.entities = [p]

    gen1 = VisualElementGenerator(game, " anchovy!")
    assert gen1.entity_id == "P123"
    assert gen1.player_name == " anchovy!"

    gen2 = VisualElementGenerator(game, "anchovy")
    assert gen2.entity_id == "P123"
    assert gen2.player_name == " anchovy!"

    gen3 = VisualElementGenerator(game, " &nbsp;anchovy!")
    assert gen3.entity_id == "P123"
    assert gen3.player_name == " anchovy!"

    gen4 = VisualElementGenerator(game, "sardine")
    assert gen4.entity_id is None
    assert gen4.player_name == "sardine"


def test_normalized_game_type_element() -> None:
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    # 1. Default config: normalized_game_type is disabled
    game = LFGame(
        game_id="test_norm_ui",
        timestamp=datetime.now(),
        game_type="Space Marines 5 Tournament Edition",
    )
    gen_default = VisualElementGenerator(game, None)
    elements_default = gen_default.generate_at(1000)

    norm_el_default = next(
        (
            el
            for el in elements_default
            if el.element_type == "text" and el.text == "Game Type: SM5"
        ),
        None,
    )
    assert norm_el_default is None

    # 2. Custom config: enable normalized_game_type
    config = {"elements": {"normalized_game_type": {"enabled": True}}}
    gen_enabled = VisualElementGenerator(game, None, config=config)
    elements_enabled = gen_enabled.generate_at(1000)

    norm_el_enabled = next(
        (
            el
            for el in elements_enabled
            if el.element_type == "text" and el.text == "SM5"
        ),
        None,
    )
    assert norm_el_enabled is not None
    assert norm_el_enabled.align == "right"
    assert norm_el_enabled.x == 0.98
    assert norm_el_enabled.y == 0.96
    assert norm_el_enabled.style.size == 14


def test_jinja_rendering_and_caching() -> None:
    from datetime import datetime
    from lfdata.model import LFGame, GameEntity
    from lfdata.video.generator import VisualElementGenerator

    # 1. Create a game and commander player entity to test player stats variables
    dt = datetime(2026, 6, 9, 20, 0, 0)
    game = LFGame(
        game_id="test_jinja_game",
        timestamp=dt,
        game_type="SM5",
        start="20260609200000",
        centre="4-43",
        arena_name="Invasion",
    )
    p = GameEntity(
        game_id="test_jinja_game",
        entity_id="P1",
        type="player",
        desc="CommanderA",
        team_index=0,
        level=1,
        category=1,  # Commander
        battlesuit="Maverick",
    )
    game.entities = [p]

    # Create dummy snapshot for player stats
    hud_gen = VisualElementGenerator(game, "CommanderA")
    from unittest.mock import MagicMock

    mock_player_state = MagicMock()
    mock_player_state.entity_id = "P1"
    mock_player_state.score = 500
    mock_player_state.lives = 15
    mock_player_state.shots = 30
    mock_player_state.missiles = 5
    mock_player_state.special_points = 20
    mock_player_state.hp = 3
    mock_player_state.max_hp = 3
    mock_player_state.role.display_name = "Commander"
    mock_player_state.role.max_lives = 30
    mock_player_state.role.max_shots = 60
    mock_player_state.role.start_missiles = 5
    mock_player_state.is_down.return_value = False
    mock_player_state.is_eliminated.return_value = False

    # Mock _get_state_at to return our mocked state
    hud_gen._get_state_at = lambda t: ({"P1": mock_player_state}, {})

    # Generate at 1000ms
    elements = hud_gen.generate_at(1000)

    # 2. Check that variables blob is populated correctly
    # game_type should be f'Game Type: {self.game.game_type}'
    assert hud_gen.current_variables["game_type"] == "Game Type: SM5"
    assert hud_gen.current_variables["centre_name"] == "Invasion"
    assert hud_gen.current_variables["player_name"] == "CommanderA"
    assert hud_gen.current_variables["player_role"] == "Commander"
    assert hud_gen.current_variables["player_score"] == "500"
    assert hud_gen.current_variables["time"] == "00:01"

    # Check default template rendering: el_game_type should show 'Game Type: SM5'
    el_gt = next(el for el in elements if el.formatted_text == "{{ game_type }}")
    assert el_gt.text == "Game Type: SM5"

    # 3. Test custom formatted_text configuration
    config = {
        "elements": {
            "player_name": {
                "enabled": True,
                "formatted_text": "Name: {{ player_name }} ({{ player_role }})",
            },
            "player_score": {
                "enabled": True,
                "formatted_text": "PTS: {{ player_score }}",
            },
        }
    }
    hud_gen_custom = VisualElementGenerator(game, "CommanderA", config=config)
    hud_gen_custom._get_state_at = lambda t: ({"P1": mock_player_state}, {})

    elements_custom = hud_gen_custom.generate_at(2000)
    el_name = next(
        el
        for el in elements_custom
        if el.formatted_text == "Name: {{ player_name }} ({{ player_role }})"
    )
    assert el_name.text == "Name: CommanderA (Commander)"

    el_score = next(
        el for el in elements_custom if el.formatted_text == "PTS: {{ player_score }}"
    )
    assert el_score.text == "PTS: 500"

    # 4. Verify caching behavior
    # Render same template and check that we hit the cache
    initial_cache_len = len(hud_gen_custom._jinja_cache)
    assert initial_cache_len > 0

    # Call _render_jinja_text directly and verify cache hit (cache size should not grow)
    res1 = hud_gen_custom._render_jinja_text(
        "PTS: {{ player_score }}",
        hud_gen_custom.current_variables,
    )
    assert res1 == "PTS: 500"
    assert len(hud_gen_custom._jinja_cache) == initial_cache_len

    # 5. Test empty string formatted_text defaults to variable name
    config_empty = {
        "elements": {
            "player_score": {
                "enabled": True,
                "formatted_text": "",
            },
        }
    }
    hud_gen_empty = VisualElementGenerator(game, "CommanderA", config=config_empty)
    hud_gen_empty._get_state_at = lambda t: ({"P1": mock_player_state}, {})

    elements_empty = hud_gen_empty.generate_at(2000)
    el_score_empty = next(
        el for el in elements_empty if el.formatted_text == "{{ player_score }}"
    )
    assert el_score_empty.text == "500"


def test_visible_end_ms_zero_stays_visible() -> None:
    """Tests that visible_end_ms set to 0 defaults to the end of the video."""
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    game = LFGame(
        game_id="test_zero_end_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )

    config = {
        "elements": {
            "player_name": {
                "enabled": True,
                "visible_end_ms": 0,
                "visible_start_ms": 1000,
            }
        }
    }

    hud_gen = VisualElementGenerator(game, None, config=config)

    el = hud_gen._create_ui_element(
        element_key="player_name",
    )

    assert el is not None
    assert el.visible_end_ms == 20000


def test_generator_keyframes_integration() -> None:
    """Verifies VisualElementGenerator evaluates keyframe animated properties."""
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video.generator import VisualElementGenerator

    # 1. Create a game with duration 10000 ms
    game = LFGame(
        game_id="test_anim_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )

    # 2. Configure game_type with animated x position and font size
    config = {
        "pregame_delay_ms": 2000,
        "elements": {
            "game_type": {
                "enabled": True,
                "x": {
                    "keyframes": [
                        {
                            "time": 0,
                            "reference": "start_of_game",
                            "value": 0.1,
                        },
                        {
                            "time": 2000,
                            "reference": "start_of_game",
                            "value": 0.5,
                        },
                    ]
                },
                "y": 0.96,
                "style": {
                    "size": {
                        "keyframes": [
                            {
                                "time": 1000,
                                "reference": "start_of_video",
                                "value": 10,
                            },
                            {
                                "time": 3000,
                                "reference": "start_of_video",
                                "value": 20,
                            },
                        ]
                    }
                },
            }
        },
    }

    hud_gen = VisualElementGenerator(game, None, config=config)

    # Test coordinate x at time_ms = 2000 (which is start_of_game + 0)
    # absolute video time 2000 ms is start_of_game + 0
    # Expected resolved x = 0.1
    import pytest

    elements1 = hud_gen.generate_at(2000)
    el_gt1 = next(
        el
        for el in elements1
        if el.element_type == "text" and el.text and "Game Type" in el.text
    )
    assert el_gt1.x == pytest.approx(0.1)

    # Test size at time_ms = 2000
    # absolute video time 2000 ms is halfway between size keyframe 1
    # (time 1000, value 10) and size keyframe 2 (time 3000, value 20).
    # Expected resolved size = 15
    assert el_gt1.style.size == 15

    # Test coordinate x at time_ms = 3000 (which is start_of_game + 1000)
    # expected resolved x = 0.3 (halfway between 0.1 and 0.5)
    elements2 = hud_gen.generate_at(3000)
    el_gt2 = next(
        el
        for el in elements2
        if el.element_type == "text" and el.text and "Game Type" in el.text
    )
    assert el_gt2.x == pytest.approx(0.3)
    # size at 3000 should be 20
    assert el_gt2.style.size == 20


def test_generator_missile_lock_and_followup() -> None:
    """Verifies that missile locking and follow-up events are tracked."""
    from datetime import datetime
    from unittest.mock import MagicMock
    from lfdata.model import LFGame, GameEvent, LFRole
    from lfdata.video import VisualElementGenerator
    from lfdata.replay.state import LFReplayPlayerState

    game = LFGame(
        game_id="test_missile_lock_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    gen = VisualElementGenerator(game, "Player1")
    gen.entity_id = "P1"
    gen.entity_names = {
        "P1": "Player1",
        "P2": "Player2",
        "P3": "Player3",
        "B1": "Base1",
    }

    mock_replay = MagicMock()
    p1_state = LFReplayPlayerState("P1", LFRole.COMMANDER, 0)
    p2_state = LFReplayPlayerState("P2", LFRole.HEAVY, 1)  # Enemy
    p3_state = LFReplayPlayerState("P3", LFRole.SCOUT, 0)  # Teammate
    mock_replay.game_state.players = {
        "P1": p1_state,
        "P2": p2_state,
        "P3": p3_state,
    }
    mock_replay.game_state.teams = {}

    gen.snapshots = [(0, {}, {}), (0, {}, {})]

    # 1. P1 locks enemy P2 at t = 1000ms
    ev1 = GameEvent(
        game_id="test_missile_lock_game",
        time=1000,
        event_type="0300",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev1, mock_replay, "")

    assert len(gen.player_event_log) == 1
    assert gen.player_event_log[0].desc == "Locking Player2"
    assert gen.player_event_log[0].time == 1000
    assert gen.player_event_log[0].event_type == "0300"

    # 2. P1 fires and hits enemy P2 at t = 3000ms (follow-up)
    ev2 = GameEvent(
        game_id="test_missile_lock_game",
        time=3000,
        event_type="0306",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev2, mock_replay, "")

    # Verifies lock event was replaced/updated and NO new event was appended
    assert len(gen.player_event_log) == 1
    assert gen.player_event_log[0].desc == "Locking Player2"
    assert gen.player_event_log[0].follow_up_desc == "Missiled Player2"
    assert gen.player_event_log[0].follow_up_time == 3000

    # Test multiline rendering before and after follow-up
    # At t = 2000ms: should show locking message
    slots_2000 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=2000,
        fade_time_ms=3000,
    )
    assert slots_2000[0] is not None
    assert slots_2000[0].text == "Locking Player2"

    # At t = 3500ms: should show follow-up missiled message
    slots_3500 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=3500,
        fade_time_ms=3000,
    )
    assert slots_3500[0] is not None
    assert slots_3500[0].text == "Missiled Player2"

    # 3. Enemy P2 locks P1 at t = 5000ms
    ev3 = GameEvent(
        game_id="test_missile_lock_game",
        time=5000,
        event_type="0300",
        actor_entity_id="P2",
        target_entity_id="P1",
    )
    gen._process_hud_event_triggers(ev3, mock_replay, "")

    assert len(gen.player_event_log) == 2
    assert gen.player_event_log[1].desc == "Locked by Player2"
    assert gen.player_event_log[1].time == 5000

    # 4. Enemy P2 fires and misses at t = 7000ms (follow-up)
    ev4 = GameEvent(
        game_id="test_missile_lock_game",
        time=7000,
        event_type="0304",
        actor_entity_id="P2",
        target_entity_id=None,
    )
    gen._process_hud_event_triggers(ev4, mock_replay, "")

    # Verifies lock event was replaced/updated
    assert len(gen.player_event_log) == 2
    assert gen.player_event_log[1].follow_up_desc == "Missile from Player2 MISSES"
    assert gen.player_event_log[1].follow_up_time == 7000

    # At t = 8000ms: should show Missile from Player2 MISSES
    slots_8000 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=8000,
        fade_time_ms=3000,
    )
    assert any(
        s is not None and s.text == "Missile from Player2 MISSES" for s in slots_8000
    )

    # 5. P1 locks teammate P3 (FRIENDLY lock) at t = 10000ms
    ev5 = GameEvent(
        game_id="test_missile_lock_game",
        time=10000,
        event_type="0300",
        actor_entity_id="P1",
        target_entity_id="P3",
    )
    gen._process_hud_event_triggers(ev5, mock_replay, "")

    assert len(gen.player_event_log) == 3
    assert gen.player_event_log[2].desc == "FRIENDLY lock Player3"

    # 6. Teammate P3 locks P1 (FRIENDLY lock by) at t = 12000ms
    ev6 = GameEvent(
        game_id="test_missile_lock_game",
        time=12000,
        event_type="0300",
        actor_entity_id="P3",
        target_entity_id="P1",
    )
    gen._process_hud_event_triggers(ev6, mock_replay, "")

    assert len(gen.player_event_log) == 4
    assert gen.player_event_log[3].desc == "FRIENDLY lock by Player3"

    # 7. Missile fire without lock event should log normally as new event
    # e.g., P1 fires missile at P2 (no lock logged before it) at t = 20000ms
    ev7 = GameEvent(
        game_id="test_missile_lock_game",
        time=20000,
        event_type="0306",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev7, mock_replay, "")
    assert len(gen.player_event_log) == 5
    assert gen.player_event_log[4].desc == "Missiled Player2"
    assert gen.player_event_log[4].time == 20000
    assert gen.player_event_log[4].follow_up_desc is None


def test_generator_player_events_in_color() -> None:
    """Verifies player_events_in_color config option behavior."""
    from datetime import datetime
    from lfdata.model import LFGame, LFRole
    from lfdata.video import VisualElementGenerator
    from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState

    game = LFGame(
        game_id="test_color_events_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    # Default config (player_events_in_color = True)
    gen = VisualElementGenerator(game, "Player1")
    gen.entity_id = "P1"
    gen.entity_names = {"P1": "Player1", "P2": "Player2"}

    players = {
        "P1": LFReplayPlayerState("P1", LFRole.COMMANDER, 0),
        "P2": LFReplayPlayerState("P2", LFRole.HEAVY, 1),
    }
    teams = {
        0: LFReplayTeamState(0, "Fire", "#ff0000"),
        1: LFReplayTeamState(1, "Earth", "#00ff00"),
    }

    # Generate with default (True)
    elements = []
    gen._add_event_hud_elements(elements, players, teams, 1000)

    # Scroller element should have player_to_color mapping
    scroller = next(el for el in elements if el.element_type == "event_scroller")
    assert scroller.player_to_color == {
        "Player1": "#ff0000",
        "Player2": "#00ff00",
    }

    # Now verify with player_events_in_color = False
    config_disabled = {"player_events_in_color": False}
    gen_disabled = VisualElementGenerator(game, "Player1", config=config_disabled)
    gen_disabled.entity_id = "P1"
    gen_disabled.entity_names = {"P1": "Player1", "P2": "Player2"}

    elements_disabled = []
    gen_disabled._add_event_hud_elements(elements_disabled, players, teams, 1000)

    # Scroller should still have the mapping
    scroller_disabled = next(
        el for el in elements_disabled if el.element_type == "event_scroller"
    )
    assert scroller_disabled.player_to_color == {
        "Player1": "#ff0000",
        "Player2": "#00ff00",
    }


def test_generator_show_hit_points_in_events() -> None:
    """Verifies prepending colored HP boxes in player events."""
    from datetime import datetime
    from unittest.mock import MagicMock
    from lfdata.model import LFGame, GameEvent, LFRole
    from lfdata.video import VisualElementGenerator
    from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState

    game = LFGame(
        game_id="test_hp_events_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    gen = VisualElementGenerator(game, "Player1")
    gen.entity_id = "P1"
    gen.entity_names = {"P1": "Player1", "P2": "Player2"}

    mock_replay = MagicMock()
    # P1 (Commander, max_hp = 3) on team 0
    p1_state = LFReplayPlayerState("P1", LFRole.COMMANDER, 0)
    p1_state.hp = 2
    # P2 (Heavy, max_hp = 3) on team 1
    p2_state = LFReplayPlayerState("P2", LFRole.HEAVY, 1)
    p2_state.hp = 1
    mock_replay.game_state.players = {"P1": p1_state, "P2": p2_state}

    t0 = LFReplayTeamState(0, "Fire", "#ff0000")
    t1 = LFReplayTeamState(1, "Earth", "#00ff00")
    mock_replay.game_state.teams = {0: t0, 1: t1}

    gen.snapshots = [(0, {}, {}), (0, {}, {})]

    # 1. P2 zaps P1 (P1 gets zapped, target is P1, max HP 3, HP 2 -> '■■□')
    ev1 = GameEvent(
        game_id="test_hp_events_game",
        time=1000,
        event_type="0205",
        actor_entity_id="P2",
        target_entity_id="P1",
    )
    gen._process_hud_event_triggers(ev1, mock_replay, "")

    assert len(gen.player_event_log) == 1
    # Check that '■■□' was prepended to 'Zapped by Player2'
    assert gen.player_event_log[0].desc == "■■□ Zapped by Player2"
    assert gen.player_event_log[0].target_color_override == {"■■□": "#ff0000"}

    # 2. P1 zaps P2 (P1 zaps someone, target is P2, max HP 3, HP 1 -> '■□□')
    ev2 = GameEvent(
        game_id="test_hp_events_game",
        time=2000,
        event_type="0205",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev2, mock_replay, "")

    assert len(gen.player_event_log) == 2
    assert gen.player_event_log[1].desc == "■□□ Zapped Player2"
    assert gen.player_event_log[1].target_color_override == {"■□□": "#00ff00"}

    # 3. Disable show_hit_points_in_events and check no boxes are prepended
    config_disabled = {"show_hit_points_in_events": False}
    gen_disabled = VisualElementGenerator(game, "Player1", config=config_disabled)
    gen_disabled.entity_id = "P1"
    gen_disabled.entity_names = {"P1": "Player1", "P2": "Player2"}
    gen_disabled.snapshots = [(0, {}, {}), (0, {}, {})]

    ev3 = GameEvent(
        game_id="test_hp_events_game",
        time=3000,
        event_type="0205",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen_disabled._process_hud_event_triggers(ev3, mock_replay, "")
    assert len(gen_disabled.player_event_log) == 1
    assert gen_disabled.player_event_log[0].desc == "Zapped Player2"
    assert gen_disabled.player_event_log[0].target_color_override is None


def test_generator_bundle_zap_events() -> None:
    """Verifies that consecutive zaps by the same player are bundled."""
    from datetime import datetime
    from unittest.mock import MagicMock
    from lfdata.model import LFGame, GameEvent, LFRole
    from lfdata.video import VisualElementGenerator
    from lfdata.replay.state import LFReplayPlayerState, LFReplayTeamState

    game = LFGame(
        game_id="test_bundle_zap_game",
        timestamp=datetime.now(),
        game_type="SM5",
    )
    # 1. Enable bundling (default)
    gen = VisualElementGenerator(game, "Player1")
    gen.entity_id = "P1"
    gen.entity_names = {"P1": "Player1", "P2": "Player2", "P3": "Player3"}

    mock_replay = MagicMock()
    p1_state = LFReplayPlayerState("P1", LFRole.COMMANDER, 0)
    p1_state.hp = 3
    p2_state = LFReplayPlayerState("P2", LFRole.HEAVY, 1)
    p2_state.hp = 3
    p3_state = LFReplayPlayerState("P3", LFRole.COMMANDER, 1)
    p3_state.hp = 2
    mock_replay.game_state.players = {
        "P1": p1_state,
        "P2": p2_state,
        "P3": p3_state,
    }

    t0 = LFReplayTeamState(0, "Fire", "#ff0000")
    t1 = LFReplayTeamState(1, "Earth", "#00ff00")
    mock_replay.game_state.teams = {0: t0, 1: t1}

    gen.snapshots = [(0, {}, {}), (0, {}, {})]

    # First zap: P1 zaps P2 (P2 max_hp 3, hp 2) at time 1000
    p2_state.hp = 2
    ev1 = GameEvent(
        game_id="test_bundle_zap_game",
        time=1000,
        event_type="0205",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev1, mock_replay, "")

    assert len(gen.player_event_log) == 1
    assert gen.player_event_log[0].desc == "■■□ Zapped Player2"

    # Second zap: P1 zaps P2 again (P2 max_hp 3, hp 1) at time 2000
    p2_state.hp = 1
    ev2 = GameEvent(
        game_id="test_bundle_zap_game",
        time=2000,
        event_type="0205",
        actor_entity_id="P1",
        target_entity_id="P2",
    )
    gen._process_hud_event_triggers(ev2, mock_replay, "")

    # Should NOT add a new entry, should bundle in the first one
    assert len(gen.player_event_log) == 1
    assert gen.player_event_log[0].zap_count == 2

    # Now verify that at time 1500 (before second zap),
    # we get '■■□ Zapped Player2'
    slots_1500 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=1500,
        fade_time_ms=3000,
    )
    assert slots_1500[0] is not None
    assert slots_1500[0].text == "■■□ Zapped Player2"
    assert slots_1500[0].target_color_override == {"■■□": "#00ff00"}

    slots_2000 = gen._get_active_multiline_lines(
        event_list=gen.player_event_log,
        time_ms=2000,
        fade_time_ms=3000,
    )
    assert slots_2000[0] is not None
    assert slots_2000[0].text == "■□□ Zapped x2 Player2"
    assert slots_2000[0].target_color_override == {"■□□": "#00ff00"}

    # Third zap: P1 zaps P3 (different player) at time 3000
    p3_state.hp = 2
    ev3 = GameEvent(
        game_id="test_bundle_zap_game",
        time=3000,
        event_type="0205",
        actor_entity_id="P1",
        target_entity_id="P3",
    )
    gen._process_hud_event_triggers(ev3, mock_replay, "")

    # Should add a new entry because it's a different target
    assert len(gen.player_event_log) == 2
    assert gen.player_event_log[1].desc == "■■□ Zapped Player3"

    # 2. Verify with bundling disabled
    config_disabled = {"bundle_zap_events": False}
    gen_disabled = VisualElementGenerator(game, "Player1", config=config_disabled)
    gen_disabled.entity_id = "P1"
    gen_disabled.entity_names = {"P1": "Player1", "P2": "Player2"}
    gen_disabled.snapshots = [(0, {}, {}), (0, {}, {})]

    # Zap twice consecutively
    p2_state.hp = 2
    gen_disabled._process_hud_event_triggers(ev1, mock_replay, "")
    p2_state.hp = 1
    gen_disabled._process_hud_event_triggers(ev2, mock_replay, "")

    assert len(gen_disabled.player_event_log) == 2
    assert gen_disabled.player_event_log[0].desc == "■■□ Zapped Player2"
    assert gen_disabled.player_event_log[1].desc == "■□□ Zapped Player2"


def test_generator_start_time_offset() -> None:
    """Verifies that visible_start_ms is calculated relative to offsets."""
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video import VisualElementGenerator

    game = LFGame(
        game_id="test_offset_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=100000,
    )
    # pregame_delay_ms = 5000, game duration = 100000
    config = {
        "pregame_delay_ms": 5000,
        "elements": {
            "el_video": {
                "enabled": True,
                "start_time_offset": "beginning of video",
                "visible_start_ms": 1000,
                "visible_end_ms": 20000,
            },
            "el_game": {
                "enabled": True,
                "start_time_offset": "beginning of game",
                "visible_start_ms": 1000,
                "visible_end_ms": 20000,
            },
            "el_end": {
                "enabled": True,
                "start_time_offset": "end of game",
                "visible_start_ms": -1000,
                "visible_end_ms": 5000,
            },
            "el_default": {
                "enabled": True,
                "visible_start_ms": 1000,
            },
        },
    }
    gen = VisualElementGenerator(game, config=config)

    # 1. beginning of video offset (offset = 0)
    # visible_start_ms = 1000, visible_end_ms = 20000
    el_video = gen._create_ui_element("el_video", element_type="text")
    assert el_video.visible_start_ms == 1000
    assert el_video.visible_end_ms == 20000

    # 2. beginning of game offset (offset = 5000)
    # visible_start_ms = 1000 + 5000 = 6000
    # visible_end_ms = 20000 + 5000 = 25000
    el_game = gen._create_ui_element("el_game", element_type="text")
    assert el_game.visible_start_ms == 6000
    assert el_game.visible_end_ms == 25000

    # 3. end of game offset (offset = 5000 + 100000 = 105000)
    # visible_start_ms = -1000 + 105000 = 104000
    # visible_end_ms = 5000 + 105000 = 110000
    el_end = gen._create_ui_element("el_end", element_type="text")
    assert el_end.visible_start_ms == 104000
    assert el_end.visible_end_ms == 110000

    # 4. default offset is beginning of video
    # visible_start_ms = 1000, visible_end_ms = video_end_ms
    el_default = gen._create_ui_element("el_default", element_type="text")
    assert el_default.visible_start_ms == 1000


def test_generator_float_font_size() -> None:
    """Verifies that floating-point font sizes resolve correctly."""
    from datetime import datetime
    from lfdata.model import LFGame
    from lfdata.video import VisualElementGenerator
    from lfdata.video.renderer import VideoGenerator as VideoFrameRenderer

    game = LFGame(
        game_id="test_float_font_game",
        timestamp=datetime.now(),
        game_type="SM5",
        duration=10000,
    )
    config = {
        "elements": {
            "el_float": {
                "enabled": True,
                "style": {
                    "size": 20.5,
                },
            },
        },
    }
    gen = VisualElementGenerator(game, config=config)
    el = gen._create_ui_element("el_float", element_type="text")
    assert el is not None
    assert el.style.size == 20.5

    # Run renderer mock verification to ensure it accepts floats
    renderer = VideoFrameRenderer(game)
    # Test text font loading with float size
    font = renderer._load_text_font("GoogleSans-Bold", "normal", 20.5)
    assert font is not None
