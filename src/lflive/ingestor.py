"""TDF stream parser and real-time game state ingestor for lflive.

This module provides `TdfIngestor`, which translates incoming tab-delimited TDF
lines into structured entity, stat, score, and state updates on `LiveGameState`,
and dispatches outbound protocol lines via `OutputEmitter`.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.ingestor import TdfIngestor
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    ingestor = TdfIngestor(game_state=state, emitter=emitter)
    ingestor.ingest_line('4\\t0000000\\t0100\\t* Mission Start *')
"""

from lfdata.model.constants.tdf import (
    TDF_RECORD_ENTITY_START,
    TDF_RECORD_EVENT,
    TDF_RECORD_INFO,
    TDF_RECORD_MISSION,
    TDF_RECORD_PLAYER_AMMO,
    TDF_RECORD_PLAYER_LIVES,
    TDF_RECORD_PLAYER_MISSILES,
    TDF_RECORD_PLAYER_STATE,
    TDF_RECORD_SCORE,
    TDF_RECORD_TEAM,
)
from lflive.constants import (
    DATA_TYPE_GAME_START_TIME,
    DATA_TYPE_GAME_TYPE,
    DATA_TYPE_NEW_GAME,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_TEAM_SCORE,
)
from lflive.dummy_player_manager import DummyPlayerManager
from lflive.emitter import OutputEmitter
from lflive.entity_registrar import EntityRegistrar
from lflive.game_event_handler import GameEventHandler
from lflive.ranking_manager import RankingManager
from lflive.state.game_state import LiveGameState


class TdfIngestor:
    """Parses live TDF lines and updates the active LiveGameState.

    Attributes:
        game_state: The LiveGameState instance being updated.
        emitter: Optional OutputEmitter broadcasting outbound protocol lines.
        ranking_manager: RankingManager tracking and emitting rank events.
        registrar: EntityRegistrar for creating teams, players, and targets.
        event_handler: GameEventHandler for processing record type 4 events.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
    ) -> None:
        """Initializes the ingestor with a target game state and emitter.

        Args:
            game_state: LiveGameState instance to update.
            emitter: Optional OutputEmitter instance for protocol messages.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.ranking_manager = RankingManager(
            game_state=self.game_state,
            emitter=self.emitter,
        )
        self.registrar = EntityRegistrar(
            game_state=self.game_state,
            emitter=self.emitter,
        )
        self.event_handler = GameEventHandler(
            game_state=self.game_state,
            emitter=self.emitter,
            ranking_manager=self.ranking_manager,
        )
        self.dummy_manager = DummyPlayerManager(
            game_state=self.game_state,
            emitter=self.emitter,
        )
        if self.emitter:
            self.emitter.add_listener(self.dummy_manager.on_line_emitted)

    @property
    def _next_player_id(self) -> int:
        """Exposes next player ID for backwards compatibility with tests."""
        return self.registrar.next_player_id

    @property
    def _entity_to_team_index(self) -> dict[str, int]:
        """Exposes entity-to-team map for backwards compatibility with tests."""
        return self.registrar.entity_to_team_index

    def reset(self) -> None:
        """Resets ID allocators and caches for a new game session.

        Usage example:
            ingestor.reset()
        """
        self.registrar.reset()
        self.ranking_manager.reset()
        self.dummy_manager.reset()
        if self.emitter:
            self.emitter.emit(DATA_TYPE_NEW_GAME, 0)

    def ingest_line(self, line: str) -> None:
        """Parses a single TDF line and applies updates to the game state.

        Args:
            line: Raw tab-delimited text line from the TDF stream.

        Usage example:
            ingestor.ingest_line('1\\t5\\tSpace Marines 5\\t...')
        """
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            return

        parts = stripped.split('\t')
        if not parts:
            return

        rec_type = parts[0]
        if rec_type == TDF_RECORD_INFO:
            self._handle_info(parts=parts)
        elif rec_type == TDF_RECORD_MISSION:
            self._handle_mission(parts=parts)
        elif rec_type == TDF_RECORD_TEAM:
            self._handle_team(parts=parts)
        elif rec_type == TDF_RECORD_ENTITY_START:
            self._handle_entity_start(parts=parts)
        elif rec_type == TDF_RECORD_EVENT:
            self._handle_event(parts=parts)
        elif rec_type == TDF_RECORD_SCORE:
            self._handle_score(parts=parts)
        elif rec_type == TDF_RECORD_PLAYER_STATE:
            self._handle_player_state(parts=parts)
        elif rec_type == TDF_RECORD_PLAYER_LIVES:
            self._handle_player_lives(parts=parts)
        elif rec_type == TDF_RECORD_PLAYER_AMMO:
            self._handle_player_ammo(parts=parts)
        elif rec_type == TDF_RECORD_PLAYER_MISSILES:
            self._handle_player_missiles(parts=parts)

    def _handle_info(self, parts: list[str]) -> None:
        """Parses record type 0 (Info)."""
        pass

    def _handle_mission(self, parts: list[str]) -> None:
        """Parses record type 1 (Mission metadata)."""
        if len(parts) >= 3:
            desc = parts[2].lower()
            if 'laserball' in desc:
                self.game_state.game_type = 'Laserball'
            else:
                self.game_state.game_type = 'SM5'

        if len(parts) >= 6:
            if len(parts) >= 7:
                start_str = parts[4]
                duration_str = parts[5]
            else:
                start_str = parts[3]
                duration_str = parts[4]

            self.game_state.start_time = start_str
            try:
                self.game_state.duration_seconds = int(duration_str) // 1000
            except ValueError:
                pass

        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_GAME_TYPE,
                0,
                self.game_state.game_type,
                self.game_state.duration_seconds,
            )
            if self.game_state.start_time:
                self.emitter.emit(
                    DATA_TYPE_GAME_START_TIME,
                    0,
                    self.game_state.start_time,
                )

    def _handle_team(self, parts: list[str]) -> None:
        """Parses record type 2 (Team registration)."""
        if len(parts) < 6:
            return
        try:
            team_index = int(parts[1])
        except ValueError:
            return

        self.registrar.register_team(
            team_index=team_index,
            name=parts[2],
            color=parts[4],
            rgb=parts[5],
        )

    def _handle_entity_start(self, parts: list[str]) -> None:
        """Parses record type 3 (Entity start registration)."""
        if len(parts) < 9:
            return

        entity_id = parts[2]
        entity_type = parts[3].lower()
        codename = parts[4]

        try:
            team_index = int(parts[5])
            category = int(parts[7])
        except ValueError:
            return

        if entity_type == 'player':
            self.registrar.register_player(
                entity_id=entity_id,
                codename=codename,
                team_index=team_index,
                category=category,
            )
        elif (
            'target' in entity_type
            or 'base' in entity_type
            or 'beacon' in entity_type
        ):
            self.registrar.register_target(
                entity_id=entity_id,
                name=codename,
                team_index=team_index,
            )

    def _handle_event(self, parts: list[str]) -> None:
        """Parses record type 4 (Game event)."""
        if len(parts) < 3:
            return

        try:
            time_offset_ms = int(parts[1])
        except ValueError:
            return

        self.game_state.current_time_ms = time_offset_ms
        event_code = parts[2]
        varies = parts[3:] if len(parts) > 3 else []
        self.event_handler.handle_event(
            time_ms=time_offset_ms,
            code=event_code,
            varies=varies,
        )

    def _handle_score(self, parts: list[str]) -> None:
        """Parses record type 5 (Authoritative score update)."""
        if len(parts) < 6:
            return
        try:
            time_offset_ms = int(parts[1])
            new_score = int(parts[5])
        except ValueError:
            return

        player = self.game_state.get_player_by_entity(entity_id=parts[2])
        if player:
            player.score = new_score
            self.game_state.record_change(
                time_offset_ms,
                'player',
                player.player_id,
                'score',
                str(new_score),
            )
            self.game_state.update_team_scores()
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_SCORE,
                    time_offset_ms,
                    player.player_id,
                    new_score,
                )
                team = self.game_state.teams.get(player.team_id)
                if team:
                    self.emitter.emit(
                        DATA_TYPE_TEAM_SCORE,
                        time_offset_ms,
                        team.team_id,
                        team.score,
                    )
            self.ranking_manager.update_rankings(time_ms=time_offset_ms)

    def _handle_player_state(self, parts: list[str]) -> None:
        """Parses record type 9 (Authoritative player operational state)."""
        if len(parts) < 4:
            return
        try:
            time_offset_ms = int(parts[1])
            new_state = int(parts[3])
        except ValueError:
            return

        player = self.game_state.get_player_by_entity(entity_id=parts[2])
        if player:
            player.state = new_state
            self.game_state.record_change(
                time_offset_ms,
                'player',
                player.player_id,
                'state',
                str(new_state),
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_STATE,
                    time_offset_ms,
                    player.player_id,
                    new_state,
                )

    def _handle_player_lives(self, parts: list[str]) -> None:
        """Parses record type 11 (Authoritative player lives update)."""
        if len(parts) < 5:
            return
        try:
            time_offset_ms = int(parts[1])
            lives_val = int(parts[4])
        except ValueError:
            return

        player = self.game_state.get_player_by_entity(entity_id=parts[2])
        if player:
            player.lives = lives_val
            self.game_state.record_change(
                time_offset_ms,
                'player',
                player.player_id,
                'lives',
                str(lives_val),
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_LIVES,
                    time_offset_ms,
                    player.player_id,
                    lives_val,
                )
            if lives_val <= 0 and player.state != 4:
                player.state = 4
                self.game_state.record_change(
                    time_offset_ms, 'player', player.player_id, 'state', '4'
                )
                if self.emitter:
                    self.emitter.emit(
                        DATA_TYPE_PLAYER_STATE,
                        time_offset_ms,
                        player.player_id,
                        4,
                    )

    def _handle_player_ammo(self, parts: list[str]) -> None:
        """Parses record type 12 (Authoritative player ammo/shots update)."""
        if len(parts) < 5:
            return
        try:
            time_offset_ms = int(parts[1])
            shots_val = int(parts[4])
        except ValueError:
            return

        player = self.game_state.get_player_by_entity(entity_id=parts[2])
        if player:
            player.shots = shots_val
            self.game_state.record_change(
                time_offset_ms,
                'player',
                player.player_id,
                'shots',
                str(shots_val),
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_SHOTS,
                    time_offset_ms,
                    player.player_id,
                    shots_val,
                )

    def _handle_player_missiles(self, parts: list[str]) -> None:
        """Parses record type 13 (Authoritative player missiles update)."""
        if len(parts) < 5:
            return
        try:
            time_offset_ms = int(parts[1])
            missiles_val = int(parts[4])
        except ValueError:
            return

        player = self.game_state.get_player_by_entity(entity_id=parts[2])
        if player:
            player.missiles = missiles_val
            self.game_state.record_change(
                time_offset_ms,
                'player',
                player.player_id,
                'missiles',
                str(missiles_val),
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_PLAYER_MISSILES,
                    time_offset_ms,
                    player.player_id,
                    missiles_val,
                )
