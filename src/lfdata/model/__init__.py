"""Data models representing LF game concepts using SQLAlchemy.

Provides database ORM models (LFGame, GameEntity, GameEvent, GameTeam, Player) and
game constant enumerations (LFRole, LFTeamColor, LFTeamType, LFCentre).

Usage example:
    from lfdata.model import LFGame, LFRole, LFTeamColor

    role = LFRole.COMMANDER
    print(f'Role {role.display_name} has {role.start_lives} starting lives.')
"""

from lfdata.model.base import Base
from lfdata.model.constants.centre import LFCentre
from lfdata.model.constants.color import LFTeamColor
from lfdata.model.constants.role import LFRole
from lfdata.model.constants.team_type import LFTeamType
from lfdata.model.gametypes.laserball_events import LaserballEvent
from lfdata.model.gametypes.laserball_notability import (
    LaserballNotabilityCondition,
    LaserballNotabilityEvaluator,
    LaserballNotabilityResult,
)
from lfdata.model.gametypes.laserball_stats import LaserballStats
from lfdata.model.gametypes.sm5_events import SM5Event
from lfdata.model.gametypes.sm5_notability import (
    Sm5NotabilityCondition,
    Sm5NotabilityEvaluator,
    Sm5NotabilityResult,
)
from lfdata.model.gametypes.sm5_stats import Sm5Stats
from lfdata.model.objects.entity import GameEntity
from lfdata.model.objects.event import GameEvent
from lfdata.model.objects.game import LFGame
from lfdata.model.objects.player import Player
from lfdata.model.objects.player_ammo_history import PlayerAmmoHistory
from lfdata.model.objects.player_lives_history import PlayerLivesHistory
from lfdata.model.objects.player_missiles_history import PlayerMissilesHistory
from lfdata.model.objects.score_history import ScoreHistory
from lfdata.model.objects.state_history import PlayerStateHistory
from lfdata.model.objects.team import GameTeam

__all__ = [
    'Base',
    'GameEntity',
    'GameEvent',
    'GameTeam',
    'LFCentre',
    'LFGame',
    'LFRole',
    'LFTeamColor',
    'LFTeamType',
    'LaserballEvent',
    'LaserballNotabilityCondition',
    'LaserballNotabilityEvaluator',
    'LaserballNotabilityResult',
    'LaserballStats',
    'Player',
    'PlayerAmmoHistory',
    'PlayerLivesHistory',
    'PlayerMissilesHistory',
    'PlayerStateHistory',
    'SM5Event',
    'ScoreHistory',
    'Sm5NotabilityCondition',
    'Sm5NotabilityEvaluator',
    'Sm5NotabilityResult',
    'Sm5Stats',
]
