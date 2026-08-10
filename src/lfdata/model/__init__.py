"""Data models representing LF game concepts using SQLAlchemy.

Provides database ORM models (LFGame, GameEntity, GameEvent, GameTeam, Player) and
game constant enumerations (LFRole, LFTeamColor, LFTeamType, LFCentre).

Usage example:
    from lfdata.model import LFGame, LFRole, LFTeamColor

    role = LFRole.COMMANDER
    print(f'Role {role.display_name} has {role.start_lives} starting lives.')
"""

from lfdata.model.base import Base
from lfdata.model.constants.color import LFTeamColor
from lfdata.model.constants.role import LFRole
from lfdata.model.constants.team_type import LFTeamType
from lfdata.model.constants.centre import LFCentre
from lfdata.model.objects.entity import GameEntity
from lfdata.model.objects.event import GameEvent
from lfdata.model.objects.game import LFGame
from lfdata.model.objects.player import Player
from lfdata.model.objects.score_history import ScoreHistory
from lfdata.model.objects.state_history import PlayerStateHistory
from lfdata.model.objects.team import GameTeam
from lfdata.model.gametypes.sm5_stats import Sm5Stats

__all__ = [
    'Base',
    'Player',
    'LFGame',
    'GameTeam',
    'GameEntity',
    'GameEvent',
    'Sm5Stats',
    'ScoreHistory',
    'PlayerStateHistory',
    'LFRole',
    'LFTeamColor',
    'LFTeamType',
    'LFCentre',
]
