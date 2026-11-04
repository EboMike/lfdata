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
        ranking: 1-based scoreboard position ranking.
        shots_fired: Total shots/zaps fired.
        shots_hit: Total shots/zaps hitting a target or opponent.
        missiles_fired: Total missiles fired.
        missiles_landed: Total missiles landing a hit.
        nukes_activated: Total nukes activated.
        nukes_detonated: Total nukes detonated.
        enemy_medic_hits: Total hits dealt to enemy medics.
        own_medic_hits: Total hits dealt to friendly medics.
        medic_nukes: Enemy medic lives stripped by nukes.
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
    ranking: int = 1
    shots_fired: int = 0
    shots_hit: int = 0
    missiles_fired: int = 0
    missiles_landed: int = 0
    nukes_activated: int = 0
    nukes_detonated: int = 0
    enemy_medic_hits: int = 0
    own_medic_hits: int = 0
    medic_nukes: int = 0

    def get_accuracy_string(self) -> str:
        """Returns player shot accuracy percentage string.

        Calculates shots hit divided by shots fired. Returns empty string if
        no shots have been fired.

        Returns:
            str: Accuracy string (e.g. '54.2%') or empty string if 0 fired.

        Usage example:
            acc = player.get_accuracy_string()
        """
        if self.shots_fired <= 0:
            return ''
        pct = (self.shots_hit / self.shots_fired) * 100.0
        return f'{pct:.1f}%'

    def get_formatted_medic_hits(self) -> str:
        """Returns formatted medic hits string.

        Displays {enemy}/{nukes}/-{own} based on non-zero components.

        Returns:
            str: Formatted medic hits representation.

        Usage example:
            hits_str = player.get_formatted_medic_hits()
        """
        if self.medic_nukes != 0 and self.own_medic_hits != 0:
            return (
                f'{self.enemy_medic_hits}/{self.medic_nukes}'
                f'/-{self.own_medic_hits}'
            )
        if self.medic_nukes != 0:
            return f'{self.enemy_medic_hits}/{self.medic_nukes}'
        if self.own_medic_hits != 0:
            return f'{self.enemy_medic_hits}/-{self.own_medic_hits}'
        return str(self.enemy_medic_hits)

    def calculate_ranking_score(self, is_laserball: bool = False) -> int:
        """Calculates player ranking score based on game mode.

        In SM5, ranking score equals the player's personal score.
        In Laserball, ranking score is computed as:
        (goals + assists) * 10000 + min(99, clears + steals) * 100
        + min(99, blocks).

        Args:
            is_laserball: Whether this is a Laserball game session.

        Returns:
            int: The calculated ranking score.

        Usage example:
            score = player.calculate_ranking_score(is_laserball=False)
        """
        if is_laserball:
            return (
                (self.goals + self.assists) * 10000
                + min(99, self.clears + self.steals) * 100
                + min(99, self.blocks)
            )
        return self.score
