"""In-memory state container for a player in lflive.

This module defines `LivePlayerState`, representing mutable real-time player
statistics, operational states, lives, shots, missiles, and scores.

Usage example:
    from lflive.state.player_state import LivePlayerState

    player = LivePlayerState(
        player_id=1,
        entity_id='#1A2B3C',
        name='Ace',
        team_id=1,
    )
    player.score += 100
"""

import dataclasses


@dataclasses.dataclass
class LivePlayerState:
    """In-memory real-time state of a single player.

    Attributes:
        player_id: Numerical primary key sent to consumers.
        entity_id: TDF entity ID string.
        name: Player codename.
        team_id: Numerical primary key of the player's team.
        role: Player role string (e.g. commander, heavy, scout).
        lives: Remaining lives count.
        shots: Remaining shots count.
        missiles: Remaining missiles count.
        special_points: Accumulated special points count.
        hitpoints: Current hitpoints remaining.
        score: Current personal score.
        goals: Goals scored (Laserball).
        assists: Assists executed (Laserball).
        blocks: Blocks executed (Laserball).
        clears: Clears executed (Laserball).
        steals: Steals executed (Laserball).
        state: Numerical player state (0=Up, 2=Resettable, 3=Down, 4=Dead).
        rapid_fire: Whether rapid fire is currently active.
    """

    player_id: int
    entity_id: str
    name: str
    team_id: int
    role: str = ''
    lives: int = 0
    shots: int = 0
    missiles: int = 0
    special_points: int = 0
    hitpoints: int = 1
    score: int = 0
    goals: int = 0
    assists: int = 0
    blocks: int = 0
    clears: int = 0
    steals: int = 0
    state: int = 0
    rapid_fire: bool = False

