"""Entity registration coordinator for lflive game sessions.

This module provides `EntityRegistrar`, which creates and initializes team,
player, and target entities within `LiveGameState` and emits protocol lines.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.entity_registrar import EntityRegistrar
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    registrar = EntityRegistrar(game_state=state, emitter=emitter)
    team = registrar.register_team(team_index=0, name='Red', color='Red', rgb='#ff0000')
"""

from lfdata.model.constants.role import LFRole
from lflive.constants import (
    DATA_TYPE_BASE_DESCRIPTION,
    DATA_TYPE_PLAYER_DESCRIPTION,
    DATA_TYPE_PLAYER_HITPOINTS,
    DATA_TYPE_PLAYER_LIVES,
    DATA_TYPE_PLAYER_MISSILES,
    DATA_TYPE_PLAYER_SCORE,
    DATA_TYPE_PLAYER_SHOTS,
    DATA_TYPE_PLAYER_SPECIAL_POINTS,
    DATA_TYPE_PLAYER_STATE,
    DATA_TYPE_TEAM_DESCRIPTION,
)
from lflive.emitter import OutputEmitter
from lflive.state.game_state import LiveGameState
from lflive.state.player_state import LivePlayerState
from lflive.state.target_state import LiveTargetState
from lflive.state.team_state import LiveTeamState


class EntityRegistrar:
    """Manages player, team, and target registration and ID allocation.

    Attributes:
        game_state: The active LiveGameState container.
        emitter: Optional OutputEmitter broadcasting outbound events.
        next_player_id: Next primary key ID to allocate to a player.
        next_target_id: Next primary key ID to allocate to a target.
        entity_to_team_index: Mapping from entity ID string to team index.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
    ) -> None:
        """Initializes the entity registrar.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.next_player_id = 1
        self.next_target_id = 1
        self.entity_to_team_index: dict[str, int] = {}

    def reset(self) -> None:
        """Resets ID allocators and caches for a new session.

        Usage example:
            registrar.reset()
        """
        self.next_player_id = 1
        self.next_target_id = 1
        self.entity_to_team_index.clear()

    def register_team(
        self,
        team_index: int,
        name: str,
        color: str,
        rgb: str,
    ) -> LiveTeamState:
        """Registers a new team and emits its protocol description.

        Args:
            team_index: 0-based team index from TDF stream.
            name: Printable team name.
            color: Color name string.
            rgb: CSS RGB hex code.

        Returns:
            LiveTeamState: Registered team state instance.

        Usage example:
            team = registrar.register_team(0, 'Fire', 'Fire', '#FF5000')
        """
        team_pk = team_index + 1
        team = self.game_state.add_team(
            team_id=team_pk,
            name=name,
            color=color,
            rgb=rgb,
        )
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_TEAM_DESCRIPTION,
                0,
                team_pk,
                name,
                rgb,
                team.dummy_player_id,
            )
        return team

    def register_player(
        self,
        entity_id: str,
        codename: str,
        team_index: int,
        category: int,
    ) -> LivePlayerState:
        """Registers a new player entity, resolving role attributes.

        Args:
            entity_id: TDF entity ID string.
            codename: Player handle or display name.
            team_index: 0-based team index from TDF.
            category: Numerical role category ID.

        Returns:
            LivePlayerState: Registered player state instance.

        Usage example:
            p = registrar.register_player('#P1', 'Ace', 0, 1)
        """
        player_pk = self.next_player_id
        self.next_player_id += 1
        team_pk = team_index + 1
        self.entity_to_team_index[entity_id] = team_index

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

        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_PLAYER_DESCRIPTION,
                0,
                player_pk,
                codename,
                entity_id,
                team_pk,
                role_str,
            )
            self.emitter.emit(DATA_TYPE_PLAYER_LIVES, 0, player_pk, lives)
            self.emitter.emit(DATA_TYPE_PLAYER_SHOTS, 0, player_pk, shots)
            self.emitter.emit(DATA_TYPE_PLAYER_MISSILES, 0, player_pk, missiles)
            self.emitter.emit(DATA_TYPE_PLAYER_SPECIAL_POINTS, 0, player_pk, 0)
            self.emitter.emit(DATA_TYPE_PLAYER_HITPOINTS, 0, player_pk, max_hp)
            self.emitter.emit(DATA_TYPE_PLAYER_STATE, 0, player_pk, 0)
            self.emitter.emit(DATA_TYPE_PLAYER_SCORE, 0, player_pk, 0)

        return player

    def register_target(
        self,
        entity_id: str,
        name: str,
        team_index: int,
    ) -> LiveTargetState:
        """Registers a base or target entity and emits its description.

        Args:
            entity_id: TDF entity ID string.
            name: Base or target name.
            team_index: 0-based team index.

        Returns:
            LiveTargetState: Registered target state instance.

        Usage example:
            t = registrar.register_target('#B1', 'Fire Base', 0)
        """
        target_pk = self.next_target_id
        self.next_target_id += 1
        team_pk = team_index + 1
        self.entity_to_team_index[entity_id] = team_index

        team = self.game_state.teams.get(team_pk)
        rgb = team.rgb if team else '#ffffff'

        target = self.game_state.add_target(
            target_id=target_pk,
            entity_id=entity_id,
            name=name,
            rgb=rgb,
        )
        if self.emitter:
            self.emitter.emit(
                DATA_TYPE_BASE_DESCRIPTION,
                0,
                target_pk,
                name,
                rgb,
            )
        return target

    def _lookup_sm5_role(self, category: int) -> tuple[str, int, int, int, int]:
        """Resolves role attributes for SM5 from role category ID.

        Args:
            category: Numerical category identifier.

        Returns:
            tuple[str, int, int, int, int]: (role_name, lives, shots, missiles, hp).
        """
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
