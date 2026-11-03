"""Overall in-memory game state container and coordinator for lflive.

This module defines `LiveGameState`, which tracks teams, players, targets,
game clocks, scoring, and historical snapshot deltas for real-time live parsing.

Usage example:
    from lflive.state.game_state import LiveGameState

    state = LiveGameState(game_type='SM5')
    state.add_team(team_id=1, name='Fire', color='Red', rgb='#ff0000')
    player = state.add_player(
        player_id=1,
        entity_id='#1A2B3C',
        name='Ace',
        team_id=1,
        role='commander',
    )
    state.record_change(
        time_ms=1000,
        entity_type='player',
        entity_id=1,
        field_name='score',
        value='100',
    )
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from lflive.db import LiveDatabase
from lflive.models import (
    LiveGameSession,
    LivePlayer,
    LiveSnapshot,
    LiveTarget,
    LiveTeam,
)
from lflive.state.player_state import LivePlayerState
from lflive.state.snapshot_entry import SnapshotEntry
from lflive.state.target_state import LiveTargetState
from lflive.state.team_state import LiveTeamState


class LiveGameState:
    """Main in-memory game state coordinator for active lflive sessions.

    Attributes:
        game_type: Game format string (e.g. SM5, Laserball).
        start_time: Start timestamp string in center local time.
        duration_seconds: Maximum scheduled game duration in seconds.
        current_time_ms: Current elapsed game time in milliseconds.
        is_game_over: Whether the game has concluded.
        ball_carrier_id: Player primary key of current ball carrier.
        round_number: Current round number for Laserball.
        is_in_round: Flag indicating whether an active round is underway.
        teams: Dictionary mapping team_id to LiveTeamState.
        players: Dictionary mapping player_id to LivePlayerState.
        players_by_entity: Dictionary mapping entity_id to LivePlayerState.
        targets: Dictionary mapping target_id to LiveTargetState.
        targets_by_entity: Dictionary mapping entity_id to LiveTargetState.
        snapshots: Chronological list of recorded state mutations.
    """

    def __init__(
        self,
        game_type: str = 'SM5',
        duration_seconds: int = 900,
        start_time: str | None = None,
    ) -> None:
        """Initializes a new live game state container.

        Args:
            game_type: Type of game being played (default SM5).
            duration_seconds: Maximum game duration in seconds.
            start_time: Optional start timestamp formatted as YYYYMMDDHHMMSSmmm.
        """
        self.game_type = game_type
        self.start_time = start_time
        self.duration_seconds = duration_seconds
        self.current_time_ms = 0
        self.is_game_over = False
        self.ball_carrier_id: int | None = None
        self.round_number = 1
        self.is_in_round = False

        self.teams: dict[int, LiveTeamState] = {}
        self.players: dict[int, LivePlayerState] = {}
        self.players_by_entity: dict[str, LivePlayerState] = {}
        self.targets: dict[int, LiveTargetState] = {}
        self.targets_by_entity: dict[str, LiveTargetState] = {}
        self.snapshots: list[SnapshotEntry] = []
        self._persisted_snapshot_count = 0

    def add_team(
        self, team_id: int, name: str, color: str, rgb: str
    ) -> LiveTeamState:
        """Registers a new team or returns existing team if already present.

        Args:
            team_id: Numerical primary key of the team.
            name: Display name of the team.
            color: Internal color name.
            rgb: CSS RGB hex code.

        Returns:
            LiveTeamState: The registered team state instance.

        Usage example:
            team = state.add_team(1, 'Fire', 'Red', '#ff0000')
        """
        if team_id not in self.teams:
            self.teams[team_id] = LiveTeamState(
                team_id=team_id,
                name=name,
                color=color,
                rgb=rgb,
            )
        return self.teams[team_id]

    def add_player(
        self,
        player_id: int,
        entity_id: str,
        name: str,
        team_id: int,
        role: str = '',
    ) -> LivePlayerState:
        """Registers a new player and updates internal entity lookups.

        Args:
            player_id: Numerical primary key of the player.
            entity_id: TDF entity ID string.
            name: Player codename.
            team_id: Numerical primary key of the player's team.
            role: Player role string.

        Returns:
            LivePlayerState: The registered player state instance.

        Usage example:
            p = state.add_player(1, '#1A2B3C', 'Ace', 1, 'scout')
        """
        if player_id not in self.players:
            player = LivePlayerState(
                player_id=player_id,
                entity_id=entity_id,
                name=name,
                team_id=team_id,
                role=role,
            )
            self.players[player_id] = player
            self.players_by_entity[entity_id] = player
        return self.players[player_id]

    def add_target(
        self, target_id: int, entity_id: str, name: str, rgb: str
    ) -> LiveTargetState:
        """Registers a new target and updates internal entity lookups.

        Args:
            target_id: Numerical primary key of the target.
            entity_id: TDF entity ID string.
            name: Name of the base or target.
            rgb: Hex RGB color code.

        Returns:
            LiveTargetState: The registered target state instance.

        Usage example:
            t = state.add_target(1, '#010001', 'Earth Base', '#00ff00')
        """
        if target_id not in self.targets:
            target = LiveTargetState(
                target_id=target_id,
                entity_id=entity_id,
                name=name,
                rgb=rgb,
            )
            self.targets[target_id] = target
            self.targets_by_entity[entity_id] = target
        return self.targets[target_id]

    def get_player_by_entity(self, entity_id: str) -> LivePlayerState | None:
        """Retrieves a player by their TDF entity ID string.

        Args:
            entity_id: TDF entity ID string to look up.

        Returns:
            LivePlayerState | None: The player instance if found, or None.

        Usage example:
            player = state.get_player_by_entity('#1A2B3C')
        """
        return self.players_by_entity.get(entity_id)

    def get_target_by_entity(self, entity_id: str) -> LiveTargetState | None:
        """Retrieves a target by its TDF entity ID string.

        Args:
            entity_id: TDF entity ID string to look up.

        Returns:
            LiveTargetState | None: The target instance if found, or None.

        Usage example:
            target = state.get_target_by_entity('#010001')
        """
        return self.targets_by_entity.get(entity_id)

    def record_change(
        self,
        time_ms: int,
        entity_type: str,
        entity_id: int,
        field_name: str,
        value: str,
    ) -> None:
        """Records a timestamped state mutation for late-join reconstruction.

        Args:
            time_ms: Elapsed game time in milliseconds.
            entity_type: Type of entity (player, team, target).
            entity_id: Primary key of the entity.
            field_name: Name of the property changed.
            value: String representation of the updated value.

        Usage example:
            state.record_change(500, 'player', 1, 'score', '100')
        """
        self.snapshots.append(
            SnapshotEntry(
                time_ms=time_ms,
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                value=value,
            )
        )

    def update_team_scores(self) -> None:
        """Recalculates cumulative scores and rankings for all teams.

        In SM5, team score is the sum of all player scores.
        In Laserball, team score is the sum of all goals scored.

        Usage example:
            state.update_team_scores()
        """
        is_laserball = self.game_type.lower() == 'laserball'
        for team in self.teams.values():
            if is_laserball:
                team.score = sum(
                    p.goals
                    for p in self.players.values()
                    if p.team_id == team.team_id
                )
            else:
                team.score = sum(
                    p.score
                    for p in self.players.values()
                    if p.team_id == team.team_id
                )

        sorted_teams = sorted(
            self.teams.values(), key=lambda t: t.score, reverse=True
        )
        for rank, team in enumerate(sorted_teams, start=1):
            team.ranking = rank

    def get_state_at(self, time_ms: int) -> 'LiveGameState':
        """Reconstructs the game state as it was at a specific millisecond offset.

        Applies registered entities and all historical snapshots up to the
        specified timestamp. Used to synthesize late-join state dumps up to
        the preroll delay boundary.

        Args:
            time_ms: Elapsed game time in milliseconds.

        Returns:
            LiveGameState: A reconstructed state snapshot at the given time.

        Usage example:
            past_state = state.get_state_at(5000)
        """
        reconstructed = LiveGameState(
            game_type=self.game_type,
            duration_seconds=self.duration_seconds,
            start_time=self.start_time,
        )
        reconstructed.current_time_ms = time_ms
        reconstructed.round_number = self.round_number

        for team in self.teams.values():
            reconstructed.add_team(
                team_id=team.team_id,
                name=team.name,
                color=team.color,
                rgb=team.rgb,
            )

        for player in self.players.values():
            reconstructed.add_player(
                player_id=player.player_id,
                entity_id=player.entity_id,
                name=player.name,
                team_id=player.team_id,
                role=player.role,
            )

        for target in self.targets.values():
            reconstructed.add_target(
                target_id=target.target_id,
                entity_id=target.entity_id,
                name=target.name,
                rgb=target.rgb,
            )

        for entry in self.snapshots:
            if entry.time_ms > time_ms:
                break
            self._apply_snapshot_entry(target_state=reconstructed, entry=entry)

        reconstructed.update_team_scores()
        return reconstructed

    def _apply_snapshot_entry(
        self, target_state: 'LiveGameState', entry: SnapshotEntry
    ) -> None:
        """Applies a single recorded snapshot mutation to a target game state.

        Args:
            target_state: The game state to modify.
            entry: The snapshot change entry to apply.
        """
        if (
            entry.entity_type == 'player'
            and entry.entity_id in target_state.players
        ):
            p = target_state.players[entry.entity_id]
            if entry.field_name == 'score':
                p.score = int(entry.value)
            elif entry.field_name == 'lives':
                p.lives = int(entry.value)
            elif entry.field_name == 'shots':
                p.shots = int(entry.value)
            elif entry.field_name == 'missiles':
                p.missiles = int(entry.value)
            elif entry.field_name == 'special_points':
                p.special_points = int(entry.value)
            elif entry.field_name == 'hitpoints':
                p.hitpoints = int(entry.value)
            elif entry.field_name == 'goals':
                p.goals = int(entry.value)
            elif entry.field_name == 'assists':
                p.assists = int(entry.value)
            elif entry.field_name == 'blocks':
                p.blocks = int(entry.value)
            elif entry.field_name == 'clears':
                p.clears = int(entry.value)
            elif entry.field_name == 'steals':
                p.steals = int(entry.value)
            elif entry.field_name == 'state':
                p.state = int(entry.value)
            elif entry.field_name == 'rapid_fire':
                p.rapid_fire = entry.value in ('1', 'True', 'true')
        elif entry.entity_type == 'game':
            if entry.field_name == 'ball_carrier_id':
                target_state.ball_carrier_id = (
                    int(entry.value) if entry.value != 'None' else None
                )
            elif entry.field_name == 'is_game_over':
                target_state.is_game_over = entry.value in ('1', 'True', 'true')

    def flush_to_database(self, db: LiveDatabase) -> None:
        """Flushes in-memory game state and new snapshots to SQLite database.

        Updates team, player, target, and session records, and writes new
        snapshot entries that have occurred since the last flush.

        Args:
            db: LiveDatabase instance providing the active database connection.

        Usage example:
            state.flush_to_database(db)
        """
        db.init_db()
        with db.get_session() as session:
            self._flush_session(session=session)
            self._flush_teams(session=session)
            self._flush_players(session=session)
            self._flush_targets(session=session)
            self._flush_snapshots(session=session)
            session.commit()

    def _flush_session(self, session: Session) -> None:
        """Upserts active game session record in the database."""
        db_sess = session.scalars(select(LiveGameSession)).first()
        if not db_sess:
            db_sess = LiveGameSession()
            session.add(db_sess)
        db_sess.game_type = self.game_type
        db_sess.start_time = self.start_time
        db_sess.duration_seconds = self.duration_seconds
        db_sess.is_active = not self.is_game_over

    def _flush_teams(self, session: Session) -> None:
        """Upserts teams in the database."""
        for team in self.teams.values():
            db_team = session.scalars(
                select(LiveTeam).filter_by(team_id=team.team_id)
            ).first()
            if not db_team:
                db_team = LiveTeam(team_id=team.team_id)
                session.add(db_team)
            db_team.name = team.name
            db_team.color = team.color
            db_team.rgb = team.rgb
            db_team.score = team.score

    def _flush_players(self, session: Session) -> None:
        """Upserts players in the database."""
        for player in self.players.values():
            db_player = session.scalars(
                select(LivePlayer).filter_by(player_id=player.player_id)
            ).first()
            if not db_player:
                db_player = LivePlayer(player_id=player.player_id)
                session.add(db_player)
            db_player.entity_id = player.entity_id
            db_player.name = player.name
            db_player.team_id = player.team_id
            db_player.role = player.role
            db_player.lives = player.lives
            db_player.shots = player.shots
            db_player.missiles = player.missiles
            db_player.special_points = player.special_points
            db_player.hitpoints = player.hitpoints
            db_player.score = player.score
            db_player.goals = player.goals
            db_player.assists = player.assists
            db_player.blocks = player.blocks
            db_player.clears = player.clears
            db_player.steals = player.steals
            db_player.state = player.state
            db_player.rapid_fire = player.rapid_fire

    def _flush_targets(self, session: Session) -> None:
        """Upserts targets in the database."""
        for target in self.targets.values():
            db_target = session.scalars(
                select(LiveTarget).filter_by(target_id=target.target_id)
            ).first()
            if not db_target:
                db_target = LiveTarget(target_id=target.target_id)
                session.add(db_target)
            db_target.entity_id = target.entity_id
            db_target.name = target.name
            db_target.rgb = target.rgb

    def _flush_snapshots(self, session: Session) -> None:
        """Inserts new snapshots since the last persistence flush."""
        new_snapshots = self.snapshots[self._persisted_snapshot_count :]
        for snap in new_snapshots:
            db_snap = LiveSnapshot(
                time_ms=snap.time_ms,
                entity_type=snap.entity_type,
                entity_id=snap.entity_id,
                field_name=snap.field_name,
                value=snap.value,
            )
            session.add(db_snap)
        self._persisted_snapshot_count = len(self.snapshots)

    def reset(self) -> None:
        """Resets all active game objects and state for a brand-new session.

        Usage example:
            state.reset()
        """
        self.current_time_ms = 0
        self.is_game_over = False
        self.ball_carrier_id = None
        self.round_number = 1
        self.is_in_round = False
        self.teams.clear()
        self.players.clear()
        self.players_by_entity.clear()
        self.targets.clear()
        self.targets_by_entity.clear()
        self.snapshots.clear()
        self._persisted_snapshot_count = 0
