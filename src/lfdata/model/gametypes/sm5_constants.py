"""Constants for Space Marines 5 (SM5) gameplay rules and mechanics.

This module defines timing durations, score values, penalty amounts, special
point costs, notability thresholds, and player state transition constants
specific to the SM5 game type as specified in the game design documentation.

Usage example:
    from lfdata.model.gametypes.sm5_constants import (
        SM5_DOWNTIME_TOTAL_MS,
        SM5_NUKE_DETONATION_TIME_MS,
    )

    print(f'Total downtime: {SM5_DOWNTIME_TOTAL_MS} ms')
"""

# Timing constants (in milliseconds)
SM5_DOWNTIME_TOTAL_MS: int = 8000
SM5_DOWNTIME_SAFE_MS: int = 4000
SM5_DOWNTIME_RESETTABLE_MS: int = 4000
SM5_NUKE_DETONATION_TIME_MS: int = 10000

# Default grace periods (in milliseconds)
DEFAULT_BOOST_GRACE_PERIOD_MS: int = 700
SM5_BOOST_GRACE_PERIOD_MS: int = 750
SM5_BOOST_AMBIGUITY_WINDOW_MS: int = 2000

# Special points costs and limits
SM5_MAX_SPECIAL_POINTS: int = 99
SM5_SPECIAL_POINTS_NUKE: int = 20
SM5_SPECIAL_POINTS_RAPID_FIRE: int = 15
SM5_SPECIAL_POINTS_MEDIC_BOOST: int = 10
SM5_SPECIAL_POINTS_AMMO_BOOST: int = 15
SM5_SPECIAL_POINTS_ZAP_ENEMY: int = 1
SM5_SPECIAL_POINTS_MISSILE_ENEMY: int = 2
SM5_BASE_CAPTURE_SPECIAL_POINTS: int = 5
SM5_BASE_DESTROY_SPECIAL_POINTS: int = SM5_BASE_CAPTURE_SPECIAL_POINTS

# Scoring constants
SM5_BASE_CAPTURE_SCORE: int = 1001
SM5_BASE_DESTROY_POINTS: int = SM5_BASE_CAPTURE_SCORE
SM5_NUKE_DETONATE_SCORE: int = 500
SM5_SCORE_NUKE_DETONATE: int = SM5_NUKE_DETONATE_SCORE
SM5_SCORE_ZAP_ENEMY: int = 100
SM5_SCORE_ZAP_TEAM: int = -100
SM5_SCORE_MISSILE_ENEMY: int = 500
SM5_SCORE_MISSILE_TEAM: int = -500
SM5_SCORE_ZAPPED_PENALTY: int = -20
SM5_SCORE_MISSILED_PENALTY: int = -100
DEFAULT_MISSION_PENALTY: int = -1000

# Lives lost per event
SM5_NUKE_LIVES_LOST: int = 3
SM5_LIVES_LOST_ZAPPED: int = 1
SM5_LIVES_LOST_MISSILED: int = 2

# Shot costs
SM5_BEACON_CLAIM_SHOTS_LOST: int = 3

# Notability condition thresholds
SM5_NOTABILITY_CLOSE_GAME_MAX_DIFF: int = 200
SM5_NOTABILITY_COMMANDER_NUKES_MIN: int = 5
SM5_NOTABILITY_HIGH_HIT_DIFF_MIN: float = 1.9
SM5_NOTABILITY_HIGH_MEDIC_HITS_MIN: int = 9
SM5_NOTABILITY_FAST_TEAM_ELIM_MAX_MS: int = 480000
SM5_NOTABILITY_ALMOST_ELIM_MAX_LIVES: int = 5
SM5_NOTABILITY_MEDIC_ZAPPED_MEDIC_MIN: int = 3
SM5_NOTABILITY_LOW_TIMES_ZAPPED_MAX: int = 5
