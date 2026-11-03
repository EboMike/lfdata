"""TDF stream parser and real-time game state ingestor for lflive.

This module provides `TdfIngestor`, which translates incoming tab-delimited TDF
lines into structured entity, stat, score, and state updates on `LiveGameState`.

Usage example:
    from lflive.ingestor import TdfIngestor
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    ingestor = TdfIngestor(game_state=state)
    ingestor.ingest_line('4\\t0000000\\t0100\\t* Mission Start *')
"""

from lfdata.model.constants.role import LFRole
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
from lfdata.model.gametypes.laserball_events import (
    LASERBALL_EVENT_ASSIST,
    LASERBALL_EVENT_BLOCK,
    LASERBALL_EVENT_CLEAR,
    LASERBALL_EVENT_GETS_BALL,
    LASERBALL_EVENT_GOAL,
    LASERBALL_EVENT_PASS,
    LASERBALL_EVENT_ROUND_END,
    LASERBALL_EVENT_ROUND_START,
    LASERBALL_EVENT_STEAL,
)
from lfdata.model.gametypes.sm5_constants import (
    SM5_BASE_CAPTURE_SCORE,
    SM5_BASE_CAPTURE_SPECIAL_POINTS,
    SM5_MAX_SPECIAL_POINTS,
    SM5_SCORE_NUKE_DETONATE,
    SM5_SPECIAL_POINTS_NUKE,
)
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_ACTIVATE_NUKE,
    SM5_EVENT_ACTIVATE_RAPID_FIRE,
    SM5_EVENT_DEACTIVATE_RAPID_FIRE,
    SM5_EVENT_DESTROY_BASE,
    SM5_EVENT_DETONATE_NUKE,
    SM5_EVENT_MISSILE_BASE_DESTROY,
    SM5_EVENT_MISSION_END,
    SM5_EVENT_MISSION_START,
)
from lflive.state.game_state import LiveGameState


class TdfIngestor:
    """Parses live TDF lines and updates the active LiveGameState.

    Attributes:
        game_state: The LiveGameState instance being updated.
    """

    def __init__(self, game_state: LiveGameState) -> None:
        """Initializes the ingestor with a target game state.

        Args:
            game_state: LiveGameState instance to update.
        """
        self.game_state = game_state
        self._next_player_id = 1
        self._next_target_id = 1
        self._entity_to_team_index: dict[str, int] = {}

    def reset(self) -> None:
        """Resets ID allocators and caches for a new game session.

        Usage example:
            ingestor.reset()
        """
        self._next_player_id = 1
        self._next_target_id = 1
        self._entity_to_team_index.clear()

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

    def _handle_team(self, parts: list[str]) -> None:
        """Parses record type 2 (Team registration)."""
        if len(parts) < 6:
            return
        try:
            team_index = int(parts[1])
        except ValueError:
            return

        team_pk = team_index + 1
        name = parts[2]
        color = parts[4]
        rgb = parts[5]

        self.game_state.add_team(
            team_id=team_pk,
            name=name,
            color=color,
            rgb=rgb,
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

        team_pk = team_index + 1
        self._entity_to_team_index[entity_id] = team_index

        if entity_type == 'player':
            self._register_player(
                entity_id=entity_id,
                codename=codename,
                team_pk=team_pk,
                category=category,
            )
        elif entity_type in ('base', 'target'):
            self._register_target(
                entity_id=entity_id,
                name=codename,
                team_pk=team_pk,
            )

    def _register_player(
        self,
        entity_id: str,
        codename: str,
        team_pk: int,
        category: int,
    ) -> None:
        """Registers a player and sets starting role attributes."""
        player_pk = self._next_player_id
        self._next_player_id += 1

        is_laserball = self.game_state.game_type.lower() == 'laserball'
        if not is_laserball:
            role_str, lives, shots, missiles, max_hp = self._lookup_sm5_role(
                category=category
            )
        else:
            role_str, lives, shots, missiles, max_hp = ('', 0, 0, 0, 1)

        player = self.game_state.add_player(
            player_id=player_pk,
            entity_id=entity_id,
            name=codename,
            team_id=team_pk,
            role=role_str,
        )
        player.lives = lives
        player.shots = shots
        player.missiles = missiles
        player.hitpoints = max_hp

    def _lookup_sm5_role(self, category: int) -> tuple[str, int, int, int, int]:
        """Resolves role attributes for Space Marines 5 from role category ID."""
        try:
            role_enum = LFRole.from_id(category)
            return (
                role_enum.display_name.lower(),
                role_enum.start_lives,
                role_enum.start_shots,
                role_enum.start_missiles,
                role_enum.max_hp,
            )
        except (ValueError, KeyError):
            return ('', 15, 30, 0, 1)

    def _register_target(self, entity_id: str, name: str, team_pk: int) -> None:
        """Registers a target or base entity."""
        target_pk = self._next_target_id
        self._next_target_id += 1

        team = self.game_state.teams.get(team_pk)
        rgb = team.rgb if team else '#ffffff'

        self.game_state.add_target(
            target_id=target_pk,
            entity_id=entity_id,
            name=name,
            rgb=rgb,
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

        if event_code == SM5_EVENT_MISSION_START:
            pass
        elif event_code == SM5_EVENT_MISSION_END:
            self.game_state.is_game_over = True
            self.game_state.record_change(
                time_offset_ms, 'game', 0, 'is_game_over', '1'
            )
        elif event_code in (
            LASERBALL_EVENT_ROUND_START,
            LASERBALL_EVENT_ROUND_END,
            LASERBALL_EVENT_GETS_BALL,
            LASERBALL_EVENT_PASS,
            LASERBALL_EVENT_GOAL,
            LASERBALL_EVENT_ASSIST,
            LASERBALL_EVENT_BLOCK,
            LASERBALL_EVENT_STEAL,
            LASERBALL_EVENT_CLEAR,
        ):
            self._handle_laserball_event(
                time_ms=time_offset_ms,
                code=event_code,
                varies=varies,
            )
        elif event_code in (
            SM5_EVENT_ACTIVATE_RAPID_FIRE,
            SM5_EVENT_DEACTIVATE_RAPID_FIRE,
            SM5_EVENT_ACTIVATE_NUKE,
            SM5_EVENT_DETONATE_NUKE,
            SM5_EVENT_DESTROY_BASE,
            SM5_EVENT_MISSILE_BASE_DESTROY,
        ):
            self._handle_sm5_event(
                time_ms=time_offset_ms,
                code=event_code,
                varies=varies,
            )

    def _handle_laserball_event(
        self, time_ms: int, code: str, varies: list[str]
    ) -> None:
        """Handles Laserball game events."""
        if code == LASERBALL_EVENT_ROUND_START:
            self.game_state.is_in_round = True
        elif code == LASERBALL_EVENT_ROUND_END:
            self.game_state.is_in_round = False
            self.game_state.round_number += 1
        elif code == LASERBALL_EVENT_GETS_BALL and varies:
            carrier = self.game_state.get_player_by_entity(entity_id=varies[0])
            if carrier:
                self.game_state.ball_carrier_id = carrier.player_id
                self.game_state.record_change(
                    time_ms,
                    'game',
                    0,
                    'ball_carrier_id',
                    str(carrier.player_id),
                )
        elif code == LASERBALL_EVENT_PASS and varies:
            target_id = (
                varies[2]
                if len(varies) >= 3
                else (varies[1] if len(varies) >= 2 else varies[0])
            )
            carrier = self.game_state.get_player_by_entity(entity_id=target_id)
            if carrier:
                self.game_state.ball_carrier_id = carrier.player_id
                self.game_state.record_change(
                    time_ms,
                    'game',
                    0,
                    'ball_carrier_id',
                    str(carrier.player_id),
                )
        elif code == LASERBALL_EVENT_GOAL and varies:
            player = self.game_state.get_player_by_entity(entity_id=varies[0])
            if player:
                player.goals += 1
                self.game_state.record_change(
                    time_ms,
                    'player',
                    player.player_id,
                    'goals',
                    str(player.goals),
                )
                self.game_state.update_team_scores()
        elif code == LASERBALL_EVENT_ASSIST and varies:
            player = self.game_state.get_player_by_entity(entity_id=varies[0])
            if player:
                player.assists += 1
                self.game_state.record_change(
                    time_ms,
                    'player',
                    player.player_id,
                    'assists',
                    str(player.assists),
                )
        elif code == LASERBALL_EVENT_BLOCK and len(varies) >= 2:
            target_id = varies[2] if len(varies) >= 3 else varies[1]
            actor = self.game_state.get_player_by_entity(entity_id=varies[0])
            target = self.game_state.get_player_by_entity(entity_id=target_id)
            if actor:
                actor.blocks += 1
                self.game_state.record_change(
                    time_ms,
                    'player',
                    actor.player_id,
                    'blocks',
                    str(actor.blocks),
                )
            if target:
                target.state = 3
                self.game_state.record_change(
                    time_ms, 'player', target.player_id, 'state', '3'
                )
        elif code == LASERBALL_EVENT_STEAL and len(varies) >= 2:
            target_id = varies[2] if len(varies) >= 3 else varies[1]
            actor = self.game_state.get_player_by_entity(entity_id=varies[0])
            target = self.game_state.get_player_by_entity(entity_id=target_id)
            if actor:
                actor.steals += 1
                self.game_state.ball_carrier_id = actor.player_id
                self.game_state.record_change(
                    time_ms,
                    'player',
                    actor.player_id,
                    'steals',
                    str(actor.steals),
                )
                self.game_state.record_change(
                    time_ms, 'game', 0, 'ball_carrier_id', str(actor.player_id)
                )
            if target:
                target.state = 3
                self.game_state.record_change(
                    time_ms, 'player', target.player_id, 'state', '3'
                )
        elif code == LASERBALL_EVENT_CLEAR and varies:
            actor = self.game_state.get_player_by_entity(entity_id=varies[0])
            if actor:
                actor.clears += 1
                self.game_state.record_change(
                    time_ms,
                    'player',
                    actor.player_id,
                    'clears',
                    str(actor.clears),
                )
            if len(varies) >= 2:
                target_id = varies[2] if len(varies) >= 3 else varies[1]
                new_c = self.game_state.get_player_by_entity(
                    entity_id=target_id
                )
                if new_c:
                    self.game_state.ball_carrier_id = new_c.player_id
                    self.game_state.record_change(
                        time_ms,
                        'game',
                        0,
                        'ball_carrier_id',
                        str(new_c.player_id),
                    )

    def _handle_sm5_event(
        self, time_ms: int, code: str, varies: list[str]
    ) -> None:
        """Handles Space Marines 5 game events."""
        if not varies:
            return
        actor = self.game_state.get_player_by_entity(entity_id=varies[0])
        if not actor:
            return

        if code == SM5_EVENT_ACTIVATE_RAPID_FIRE:
            actor.rapid_fire = True
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'rapid_fire', '1'
            )
        elif code == SM5_EVENT_DEACTIVATE_RAPID_FIRE:
            actor.rapid_fire = False
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'rapid_fire', '0'
            )
        elif code == SM5_EVENT_ACTIVATE_NUKE:
            actor.special_points = max(
                0, actor.special_points - SM5_SPECIAL_POINTS_NUKE
            )
            self.game_state.record_change(
                time_ms,
                'player',
                actor.player_id,
                'special_points',
                str(actor.special_points),
            )
        elif code == SM5_EVENT_DETONATE_NUKE:
            actor.score += SM5_SCORE_NUKE_DETONATE
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'score', str(actor.score)
            )
            self.game_state.update_team_scores()
        elif code in (SM5_EVENT_DESTROY_BASE, SM5_EVENT_MISSILE_BASE_DESTROY):
            actor.score += SM5_BASE_CAPTURE_SCORE
            actor.special_points = min(
                SM5_MAX_SPECIAL_POINTS,
                actor.special_points + SM5_BASE_CAPTURE_SPECIAL_POINTS,
            )
            self.game_state.record_change(
                time_ms, 'player', actor.player_id, 'score', str(actor.score)
            )
            self.game_state.record_change(
                time_ms,
                'player',
                actor.player_id,
                'special_points',
                str(actor.special_points),
            )
            self.game_state.update_team_scores()

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
            if lives_val <= 0 and player.state != 4:
                player.state = 4
                self.game_state.record_change(
                    time_offset_ms, 'player', player.player_id, 'state', '4'
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
