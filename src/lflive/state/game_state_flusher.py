"""Database sync utility for lflive game state.

This module provides `GameStateFlusher` to flush in-memory LiveGameState
and historical snapshot entries to a SQLite database via SQLAlchemy.

Usage example:
    from lflive.db import LiveDatabase
    from lflive.state.game_state import LiveGameState
    from lflive.state.game_state_flusher import GameStateFlusher

    db = LiveDatabase()
    state = LiveGameState()
    GameStateFlusher.flush(game_state=state, db=db)
"""

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from lflive.state.game_state import LiveGameState


class GameStateFlusher:
    """Synchronizes in-memory game state and snapshot records to SQLite.

    This class extracts database persistence logic away from LiveGameState
    to adhere to single-responsibility guidelines and file length constraints.
    """

    @classmethod
    def flush(cls, game_state: 'LiveGameState', db: LiveDatabase) -> None:
        """Flushes in-memory game state and new snapshots to SQLite database.

        Updates team, player, target, and session records, and writes new
        snapshot entries that have occurred since the last flush.

        Args:
            game_state: LiveGameState instance to persist.
            db: LiveDatabase instance providing the active database connection.

        Usage example:
            GameStateFlusher.flush(game_state=state, db=db)
        """
        db.init_db()
        with db.get_session() as session:
            cls._flush_session(game_state=game_state, session=session)
            cls._flush_teams(game_state=game_state, session=session)
            cls._flush_players(game_state=game_state, session=session)
            cls._flush_targets(game_state=game_state, session=session)
            cls._flush_snapshots(game_state=game_state, session=session)
            session.commit()

    @classmethod
    def _flush_session(
        cls, game_state: 'LiveGameState', session: Session
    ) -> None:
        """Upserts active game session record in the database."""
        db_sess = session.scalars(select(LiveGameSession)).first()
        if not db_sess:
            db_sess = LiveGameSession()
            session.add(db_sess)
        db_sess.game_type = game_state.game_type
        db_sess.start_time = game_state.start_time
        db_sess.duration_seconds = game_state.duration_seconds
        db_sess.is_active = not game_state.is_game_over

    @classmethod
    def _flush_teams(
        cls, game_state: 'LiveGameState', session: Session
    ) -> None:
        """Upserts teams in the database."""
        for team in game_state.teams.values():
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

    @classmethod
    def _flush_players(
        cls, game_state: 'LiveGameState', session: Session
    ) -> None:
        """Upserts players in the database."""
        for player in game_state.players.values():
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

    @classmethod
    def _flush_targets(
        cls, game_state: 'LiveGameState', session: Session
    ) -> None:
        """Upserts targets in the database."""
        for target in game_state.targets.values():
            db_target = session.scalars(
                select(LiveTarget).filter_by(target_id=target.target_id)
            ).first()
            if not db_target:
                db_target = LiveTarget(target_id=target.target_id)
                session.add(db_target)
            db_target.entity_id = target.entity_id
            db_target.name = target.name
            db_target.rgb = target.rgb

    @classmethod
    def _flush_snapshots(
        cls, game_state: 'LiveGameState', session: Session
    ) -> None:
        """Appends new snapshot mutation rows since the previous flush."""
        new_snapshots = game_state.snapshots[
            game_state._persisted_snapshot_count :
        ]
        for snap in new_snapshots:
            db_snap = LiveSnapshot(
                time_ms=snap.time_ms,
                entity_type=snap.entity_type,
                entity_id=snap.entity_id,
                field_name=snap.field_name,
                value=snap.value,
            )
            session.add(db_snap)
        game_state._persisted_snapshot_count = len(game_state.snapshots)
