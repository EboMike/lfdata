"""Ranking calculation and broadcast coordinator for lflive.

This module provides `RankingManager`, which tracks and broadcasts player
and team score rankings to connected consumers when the ranking order changes.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.ranking_manager import RankingManager
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    ranking_mgr = RankingManager(game_state=state, emitter=emitter)
    ranking_mgr.update_rankings(time_ms=1000)
"""

from lflive.constants import DATA_TYPE_PLAYER_RANKING, DATA_TYPE_TEAM_RANKING
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState


class RankingManager:
    """Calculates, tracks, and emits player and team rankings for lflive.

    Attributes:
        game_state: The active LiveGameState container.
        emitter: Optional OutputEmitter broadcasting outbound events.
        last_player_rankings: Previously broadcast player rankings by team ID.
        last_team_ranking: Previously broadcast team ID ranking list.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
    ) -> None:
        """Initializes the ranking manager.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.last_player_rankings: dict[int, list[int]] = {}
        self.last_team_ranking: list[int] | None = None

    def reset(self) -> None:
        """Resets cached ranking states for a new session.

        Usage example:
            ranking_mgr.reset()
        """
        self.last_player_rankings.clear()
        self.last_team_ranking = None

    def calculate_player_rankings(self) -> dict[int, list[int]]:
        """Calculates current ordered list of player primary keys by team.

        Returns:
            dict[int, list[int]]: Player IDs ordered by rank within their team.

        Usage example:
            p_ranks = ranking_mgr.calculate_player_rankings()
        """
        return self.game_state.update_player_rankings()

    def calculate_team_ranking(self) -> list[int]:
        """Calculates current ordered list of team primary keys.

        Returns:
            list[int]: Team IDs ordered by rank (highest score first).

        Usage example:
            t_ranks = ranking_mgr.calculate_team_ranking()
        """
        self.game_state.update_team_scores()
        return self.game_state.get_team_ranking()

    def update_rankings(self, time_ms: int) -> tuple[bool, bool]:
        """Recalculates rankings and emits protocol events if ordering changed.

        Emits Type 26 (player ranking within team) and Type 27 (team ranking)
        events with comma-separated primary keys if the new ranking order
        differs from the previously emitted ranking.

        Args:
            time_ms: Elapsed game time in milliseconds.

        Returns:
            tuple[bool, bool]: Tuple of (player_ranking_changed,
                team_ranking_changed).

        Usage example:
            changed_p, changed_t = ranking_mgr.update_rankings(time_ms=5000)
        """
        player_rankings = self.calculate_player_rankings()
        team_ranking = self.calculate_team_ranking()
        player_changed = False
        team_changed = False

        for team_id, p_ranking in player_rankings.items():
            if p_ranking and p_ranking != self.last_player_rankings.get(
                team_id
            ):
                self.last_player_rankings[team_id] = list(p_ranking)
                player_changed = True
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_PLAYER_RANKING,
                        time_ms,
                        team_id,
                        ','.join(str(p) for p in p_ranking),
                    )

        if team_ranking and team_ranking != self.last_team_ranking:
            self.last_team_ranking = list(team_ranking)
            team_changed = True
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_TEAM_RANKING,
                    time_ms,
                    ','.join(str(t) for t in team_ranking),
                )

        return player_changed, team_changed
