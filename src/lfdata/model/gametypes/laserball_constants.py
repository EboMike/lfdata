"""Constants for Laserball gameplay rules, statistics, and scoring.

This module defines ranking score calculation multipliers and stat caps
specific to the Laserball game type.

Usage example:
    from lfdata.model.gametypes.laserball_constants import (
        LASERBALL_GOAL_SCORE_MULTIPLIER,
    )

    print(f'Goal multiplier: {LASERBALL_GOAL_SCORE_MULTIPLIER}')
"""

# Scoring multipliers for ranking calculation
LASERBALL_GOAL_SCORE_MULTIPLIER: int = 10000
LASERBALL_CLEAR_STEAL_SCORE_MULTIPLIER: int = 100

# Maximum cap for secondary statistics (blocks, clears, steals) in score calc
LASERBALL_STAT_CAP: int = 99

# Laserball notability condition thresholds
LASERBALL_NOTABILITY_MIN_GOALS: int = 1
LASERBALL_NOTABILITY_MIN_ASSISTS: int = 1
LASERBALL_NOTABILITY_MIN_STEALS: int = 2
LASERBALL_NOTABILITY_HIGH_HIT_DIFF_MIN: float = 1.4
LASERBALL_NOTABILITY_MIN_CLEARS: int = 2
LASERBALL_NOTABILITY_EXTRA_BLOCKS_THRESHOLD: int = 20
