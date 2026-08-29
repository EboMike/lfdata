"""Classes representing the state of players, teams, and the game during a replay.

This module provides mutable state containers (`LFReplayPlayerState`, `LFReplayTeamState`,
and `LFReplayGameState`) for tracking active player statistics, team scores, and overall
game status during playback simulation.

Usage example:
    from lfdata.replay.state import LFReplayGameState, LFReplayPlayerState
    from lfdata.model import LFRole

    pstate = LFReplayPlayerState(entity_id='P1', role=LFRole.COMMANDER, team_index=0)
    print(f'Player {pstate.entity_id} starting lives: {pstate.lives}')
"""

from lfdata.model import LFRole, PlayerStateHistory


class LFReplayPlayerState:
    """Mutable snapshot of a single player entity during game replay.

    Attributes:
        entity_id: Entity ID string of the player.
        role: LFRole enum of the player.
        team_index: Team index integer assigned to the player.
        lives: Current remaining lives count.
        shots: Current remaining shots count.
        missiles: Current remaining missiles count.
        score: Current player score integer.
        special_points: Property returning special points value.
        max_hp: Maximum hit points (shields) integer.
        hp: Current hit points integer.
        downtime_ends_at_ms: Timestamp in milliseconds when downtime ends.
        resettable_starts_at_ms: Timestamp in milliseconds when resettable status starts.
        just_went_down_at_ms: Optional timestamp in milliseconds when player went down.
        captured_bases: Set of captured base entity ID strings.
        nuke_activated_at_ms: Optional timestamp in milliseconds when nuke was activated.
        nuke_cancel_details: Optional LFNukeCancelDetails instance.
        state_history: List of PlayerStateHistory entries.
        times_zapped: Times player was zapped.
        times_zapped_opponents: Times player zapped players on other teams.
        times_zapped_someone: Deprecated alias for times_zapped_opponents.
        hit_diff: Property returning ratio of opponent zaps to times zapped.
    """

    def __init__(
        self,
        entity_id: str,
        role: LFRole,
        team_index: int,
        state_history: list[PlayerStateHistory] | None = None,
    ) -> None:
        """Initializes the player state with role-based start values.

        Args:
            entity_id: The ID of the game entity.
            role: The LFRole enum representing the player's role.
            team_index: The team index the player belongs to.
            state_history: Optional list of authoritative state history entries
                parsed from type 9 records.
        """
        self.entity_id = entity_id
        self.role = role
        self.team_index = team_index
        self.lives = role.start_lives
        self.shots = role.start_shots
        self.missiles = role.start_missiles
        self.score = 0
        self._special_points = 0
        self.max_hp = role.max_hp
        self.hp = role.max_hp
        self.downtime_ends_at_ms = 0
        self.resettable_starts_at_ms = 0
        self.just_went_down_at_ms: int | None = None
        self.captured_bases: set[str] = set()
        self.has_rapid_fire = False
        self.nukes_activated: int = 0
        self.nukes_detonated: int = 0
        self.nuke_cancels: int = 0
        self.own_nuke_cancels: int = 0
        self.penalties: int = 0
        self.times_zapped: int = 0
        self.times_zapped_opponents: int = 0
        self.state_history: list[PlayerStateHistory] | None = state_history

    @property
    def has_authoritative_state(self) -> bool:
        """Returns True if authoritative type 9 state history is present."""
        return bool(self.state_history)

    def get_state_at(self, current_time_ms: int) -> int:
        """Returns the player's authoritative state at current_time_ms.

        State values:
        - 0: Player is up
        - 3: Player is down and not resettable
        - 2: Player is resettable

        Args:
            current_time_ms: Timestamp in milliseconds.

        Returns:
            int: 0 if up, 3 if down and not resettable, 2 if resettable.
        """
        if not self.state_history:
            return 0
        latest_state = 0
        for entry in self.state_history:
            if entry.time <= current_time_ms:
                latest_state = entry.state
            else:
                break
        return latest_state

    def is_eliminated(self) -> bool:
        """Returns True if the player has no lives left and is out of the
        game.
        """
        return self.lives <= 0

    def is_down(self, current_time_ms: int) -> bool:
        """Returns True if the player is currently deactivated / down.

        Args:
            current_time_ms: The current millisecond timestamp.

        Returns:
            bool: True if the player is currently down, False otherwise.
        """
        if self.has_authoritative_state:
            return self.get_state_at(current_time_ms) in (2, 3)
        return current_time_ms < self.downtime_ends_at_ms

    def is_resettable(self, current_time_ms: int) -> bool:
        """Returns True if the player is currently in a resettable down state.

        Args:
            current_time_ms: The current millisecond timestamp.

        Returns:
            bool: True if resettable down state, False otherwise.
        """
        if self.has_authoritative_state:
            return self.get_state_at(current_time_ms) == 2
        return (
            self.is_down(current_time_ms)
            and current_time_ms >= self.resettable_starts_at_ms
        )

    def get_down_start_time_ms(self, current_time_ms: int) -> int | None:
        """Returns the timestamp when current down state started, if down.

        Args:
            current_time_ms: The current millisecond timestamp.

        Returns:
            int | None: Down start timestamp in ms, or None if not down.
        """
        if self.has_authoritative_state:
            if not self.state_history:
                return None
            down_start: int | None = None
            for entry in self.state_history:
                if entry.time > current_time_ms:
                    break
                if entry.state in (2, 3):
                    if down_start is None:
                        down_start = entry.time
                else:
                    down_start = None
            return down_start
        return self.just_went_down_at_ms

    def can_receive_resupply(
        self, current_time_ms: int, grace_period_ms: int = 700
    ) -> bool:
        """Checks if the player can receive resupply or team boost.

        A player is eligible to receive resupply if they are not down, or if
        they transitioned to down within the configurable grace period.

        Args:
            current_time_ms: The current millisecond timestamp.
            grace_period_ms: Grace period in milliseconds (defaults to 700,
                representing 0.7 seconds).

        Returns:
            bool: True if eligible, False otherwise.
        """
        if self.is_eliminated():
            return False
        if not self.is_down(current_time_ms):
            return True
        down_start = self.get_down_start_time_ms(current_time_ms)
        if down_start is not None:
            elapsed_ms = current_time_ms - down_start
            return 0 <= elapsed_ms <= grace_period_ms
        return False

    def update_downtime(self, current_time_ms: int) -> None:
        """Restores player's HP if active / up, or zeroes HP if down.

        Args:
            current_time_ms: The current millisecond timestamp.
        """
        if self.is_eliminated():
            self.hp = 0
            return
        if self.has_authoritative_state:
            state = self.get_state_at(current_time_ms)
            if state == 0:
                self.hp = self.max_hp
            else:
                self.hp = 0
        else:
            if self.hp == 0 and current_time_ms >= self.downtime_ends_at_ms:
                self.hp = self.max_hp
                self.just_went_down_at_ms = None

    def resupply_lives_from_medic(self) -> None:
        """Adds lives to player based on role-specific medic resupply values."""
        if self.is_eliminated():
            return
        self.lives = min(
            self.role.max_lives, self.lives + self.role.medic_lives_gain
        )

    def resupply_shots_from_ammo(self) -> None:
        """Adds shots to player based on role-specific ammo resupply values."""
        if self.is_eliminated():
            return
        self.shots = min(
            self.role.max_shots, self.shots + self.role.ammo_shots_gain
        )

    @property
    def special_points(self) -> int:
        """Returns the player's special points.

        Gets the number of special points the player currently has.

        Returns:
            int: The current special points, up to 99.
        """
        return self._special_points

    @special_points.setter
    def special_points(self, value: int) -> None:
        """Sets the player's special points, clamped between 0 and 99.

        Sets the number of special points, ensuring it never goes below 0 or
        exceeds 99.

        Args:
            value: The new special points value.
        """
        self._special_points = max(0, min(99, value))

    @property
    def times_zapped_someone(self) -> int:
        """Alias for times_zapped_opponents."""
        return self.times_zapped_opponents

    @times_zapped_someone.setter
    def times_zapped_someone(self, value: int) -> None:
        """Setter for times_zapped_someone alias."""
        self.times_zapped_opponents = value

    @property
    def hit_diff(self) -> float | None:
        """Returns the player's hit differential (hit diff).

        The hit diff is the number of times the player zapped players on
        other teams divided by the number of times the player got zapped.
        Missiles, nukes, friendly fire, and base hits do not factor into this
        equation. If the player was never zapped, the hit diff is None.

        Returns:
            float | None: The hit diff ratio, or None if the player was never
                zapped.
        """
        if self.times_zapped == 0:
            return None
        return self.times_zapped_opponents / self.times_zapped


class LFReplayTeamState:
    """Mutable snapshot of a single team's score and ranking during game replay.

    Attributes:
        team_index: Team index integer.
        name: Printable name string of the team.
        color_rgb: CSS RGB hex color string.
        score: Cumulative team score integer.
        ranking: Current team rank position integer (1-based).
    """

    def __init__(
        self, team_index: int, name: str, color_rgb: str = '#ffffff'
    ) -> None:
        """Initializes the team state.

        Args:
            team_index: The team index.
            name: The team name.
            color_rgb: The RGB hex color code.
        """
        self.team_index = team_index
        self.name = name
        self.color_rgb = color_rgb
        self.score = 0
        self.ranking = 1


class LFReplayGameState:
    """Overall game state container tracking active players and teams during replay.

    Attributes:
        players: Mapping of entity ID strings to LFReplayPlayerState instances.
        teams: Mapping of team index integers to LFReplayTeamState instances.
    """

    def __init__(
        self,
        players: list[LFReplayPlayerState],
        teams: list[LFReplayTeamState],
    ) -> None:
        """Initializes the game state.

        Args:
            players: List of player states.
            teams: List of team states.
        """
        self.players = {p.entity_id: p for p in players}
        self.teams = {t.team_index: t for t in teams}

    def update_team_scores_and_rankings(self) -> None:
        """Recalculates team scores and rankings based on player scores."""
        for team in self.teams.values():
            team.score = sum(
                p.score
                for p in self.players.values()
                if p.team_index == team.team_index
            )

        sorted_teams = sorted(
            self.teams.values(), key=lambda t: t.score, reverse=True
        )
        for rank, team in enumerate(sorted_teams, 1):
            team.ranking = rank
