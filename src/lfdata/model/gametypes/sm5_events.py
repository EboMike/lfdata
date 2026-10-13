"""Enums and constants representing Space Marines 5 (SM5) game events.

This module defines event type constants, metadata dataclasses, and the
SM5Event enumeration for all events that occur in SM5 games.

Usage example:
    from lfdata.model.gametypes.sm5_events import (
        SM5Event,
        SM5_EVENT_MISSILE_MISS,
    )

    ev = SM5Event.from_id(SM5_EVENT_MISSILE_MISS)
    if ev:
        print(f'{ev.display_name}: {ev.description}')
"""

import dataclasses
import enum

# Mission lifecycle events (01xx)
SM5_EVENT_MISSION_START: str = '0100'
SM5_EVENT_MISSION_END: str = '0101'

# Shot / Zap events (02xx)
SM5_EVENT_SHOT_EMPTY: str = '0200'
SM5_EVENT_MISS: str = '0201'
SM5_EVENT_MISS_BASE: str = '0202'
SM5_EVENT_HIT_BASE: str = '0203'
SM5_EVENT_DESTROY_BASE: str = '0204'
SM5_EVENT_DAMAGED_OPPONENT: str = '0205'
SM5_EVENT_DOWNED_OPPONENT: str = '0206'
SM5_EVENT_DAMAGED_TEAM: str = '0207'
SM5_EVENT_DOWNED_TEAM: str = '0208'
SM5_EVENT_WARBOT_ZAP: str = '0209'

# Missile events (03xx)
SM5_EVENT_LOCKING: str = '0300'
SM5_EVENT_MISSILE_BASE_MISS: str = '0301'
SM5_EVENT_MISSILE_BASE_DAMAGE: str = '0302'
SM5_EVENT_MISSILE_BASE_DESTROY: str = '0303'
SM5_EVENT_MISSILE_MISS: str = '0304'
SM5_EVENT_MISSILE_DAMAGE_OPPONENT: str = '0305'
SM5_EVENT_MISSILE_DOWN_OPPONENT: str = '0306'
SM5_EVENT_MISSILE_DAMAGE_TEAM: str = '0307'
SM5_EVENT_MISSILE_DOWN_TEAM: str = '0308'

# Special power events (04xx)
SM5_EVENT_ACTIVATE_RAPID_FIRE: str = '0400'
SM5_EVENT_DEACTIVATE_RAPID_FIRE: str = '0401'
SM5_EVENT_ACTIVATE_NUKE: str = '0404'
SM5_EVENT_DETONATE_NUKE: str = '0405'

# Resupply / Boost events (05xx)
SM5_EVENT_RESUPPLY_AMMO: str = '0500'
SM5_EVENT_RESUPPLY_LIVES: str = '0502'
SM5_EVENT_AMMO_BOOST: str = '0510'
SM5_EVENT_LIFE_BOOST: str = '0512'

# Penalty event (06xx)
SM5_EVENT_PENALTY: str = '0600'

# Gamification events (09xx)
SM5_EVENT_ACHIEVEMENT: str = '0900'
SM5_EVENT_REWARD: str = '0902'

# Beacon / Base awarded events (0Bxx)
SM5_EVENT_CLAIM_BEACON: str = '0B00'
SM5_EVENT_BASE_AWARDED: str = '0B03'

# Inferred events
SM5_EVENT_NUKE_CANCEL: str = 'nuke_cancel'

# Common aliases without SM5_ prefix for general use
EVENT_MISSION_START: str = SM5_EVENT_MISSION_START
EVENT_MISSION_END: str = SM5_EVENT_MISSION_END
EVENT_PENALTY: str = SM5_EVENT_PENALTY
EVENT_MISSILE_MISS: str = SM5_EVENT_MISSILE_MISS


@dataclasses.dataclass(frozen=True)
class SM5EventInfo:
    """Metadata for a Space Marines 5 event type.

    Attributes:
        event_id: The 4-digit hexadecimal event code string.
        name: Short identifier name for the event.
        description: Human-readable description of the event.
    """

    event_id: str
    name: str
    description: str


class SM5Event(enum.Enum):
    """Enumeration of event types in Space Marines 5 games.

    Attributes:
        MISSION_START: Mission start event.
        MISSION_END: Mission end event.
        SHOT_EMPTY: Empty shot event.
        MISS: Player zaps and misses.
        MISS_BASE: Player zaps base and misses.
        HIT_BASE: Player zaps base.
        DESTROY_BASE: Player captures base via zap.
        DAMAGED_OPPONENT: Player zaps enemy without downing them.
        DOWNED_OPPONENT: Player zaps enemy and downs them.
        DAMAGED_TEAM: Player zaps teammate without downing them.
        DOWNED_TEAM: Player zaps teammate and downs them.
        WARBOT_ZAP: Warbot zaps player.
        LOCKING: Player locks on target with missile.
        MISSILE_BASE_MISS: Player locks missile at base and misses.
        MISSILE_BASE_DAMAGE: Player fires missile at base without destroying it.
        MISSILE_BASE_DESTROY: Player captures base via missile.
        MISSILE_MISS: Player fires missile and misses.
        MISSILE_DAMAGE_OPPONENT: Player missiles enemy without downing.
        MISSILE_DOWN_OPPONENT: Player missiles enemy and downs them.
        MISSILE_DAMAGE_TEAM: Player missiles teammate without downing.
        MISSILE_DOWN_TEAM: Player missiles teammate and downs them.
        ACTIVATE_RAPID_FIRE: Player activates rapid fire.
        DEACTIVATE_RAPID_FIRE: Player deactivates rapid fire.
        ACTIVATE_NUKE: Player activates nuke.
        DETONATE_NUKE: Player detonates nuke.
        RESUPPLY_AMMO: Player resupplies teammate with ammo.
        RESUPPLY_LIVES: Player resupplies teammate with lives.
        AMMO_BOOST: Player resupplies ammo to entire team.
        LIFE_BOOST: Player resupplies lives to entire team.
        PENALTY: Player receives penalty from referee.
        ACHIEVEMENT: Player completes achievement.
        REWARD: Player earns reward.
        CLAIM_BEACON: Player claims beacon.
        BASE_AWARDED: Player is awarded a base.
        NUKE_CANCEL: Inferred nuke cancellation.
    """

    MISSION_START = SM5EventInfo(
        event_id=SM5_EVENT_MISSION_START,
        name='MISSION_START',
        description='Mission starts.',
    )
    MISSION_END = SM5EventInfo(
        event_id=SM5_EVENT_MISSION_END,
        name='MISSION_END',
        description='Mission ends.',
    )
    SHOT_EMPTY = SM5EventInfo(
        event_id=SM5_EVENT_SHOT_EMPTY,
        name='SHOT_EMPTY',
        description='Empty shot.',
    )
    MISS = SM5EventInfo(
        event_id=SM5_EVENT_MISS,
        name='MISS',
        description='Player zaps and misses.',
    )
    MISS_BASE = SM5EventInfo(
        event_id=SM5_EVENT_MISS_BASE,
        name='MISS_BASE',
        description='Player zaps base and misses.',
    )
    HIT_BASE = SM5EventInfo(
        event_id=SM5_EVENT_HIT_BASE,
        name='HIT_BASE',
        description='Player zaps base.',
    )
    DESTROY_BASE = SM5EventInfo(
        event_id=SM5_EVENT_DESTROY_BASE,
        name='DESTROY_BASE',
        description='Player zaps and captures base.',
    )
    DAMAGED_OPPONENT = SM5EventInfo(
        event_id=SM5_EVENT_DAMAGED_OPPONENT,
        name='DAMAGED_OPPONENT',
        description='Player zaps enemy, enemy is not down.',
    )
    DOWNED_OPPONENT = SM5EventInfo(
        event_id=SM5_EVENT_DOWNED_OPPONENT,
        name='DOWNED_OPPONENT',
        description='Player zaps enemy, enemy is down.',
    )
    DAMAGED_TEAM = SM5EventInfo(
        event_id=SM5_EVENT_DAMAGED_TEAM,
        name='DAMAGED_TEAM',
        description='Player zaps own teammate, teammate is not down.',
    )
    DOWNED_TEAM = SM5EventInfo(
        event_id=SM5_EVENT_DOWNED_TEAM,
        name='DOWNED_TEAM',
        description='Player zaps own teammate, teammate is down.',
    )
    WARBOT_ZAP = SM5EventInfo(
        event_id=SM5_EVENT_WARBOT_ZAP,
        name='WARBOT_ZAP',
        description='Warbot zaps player.',
    )
    LOCKING = SM5EventInfo(
        event_id=SM5_EVENT_LOCKING,
        name='LOCKING',
        description='Player locks on target with missile.',
    )
    MISSILE_BASE_MISS = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_BASE_MISS,
        name='MISSILE_BASE_MISS',
        description='Player locks missile at base and misses.',
    )
    MISSILE_BASE_DAMAGE = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_BASE_DAMAGE,
        name='MISSILE_BASE_DAMAGE',
        description='Player fires missile at base, base not destroyed.',
    )
    MISSILE_BASE_DESTROY = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_BASE_DESTROY,
        name='MISSILE_BASE_DESTROY',
        description='Player fires missile at base, base captured.',
    )
    MISSILE_MISS = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_MISS,
        name='MISSILE_MISS',
        description='Player fires missile and misses.',
    )
    MISSILE_DAMAGE_OPPONENT = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_DAMAGE_OPPONENT,
        name='MISSILE_DAMAGE_OPPONENT',
        description='Player fires missile at enemy, enemy not down.',
    )
    MISSILE_DOWN_OPPONENT = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_DOWN_OPPONENT,
        name='MISSILE_DOWN_OPPONENT',
        description='Player fires missile at enemy, enemy is down.',
    )
    MISSILE_DAMAGE_TEAM = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_DAMAGE_TEAM,
        name='MISSILE_DAMAGE_TEAM',
        description='Player fires missile at teammate, teammate not down.',
    )
    MISSILE_DOWN_TEAM = SM5EventInfo(
        event_id=SM5_EVENT_MISSILE_DOWN_TEAM,
        name='MISSILE_DOWN_TEAM',
        description='Player fires missile at teammate, teammate is down.',
    )
    ACTIVATE_RAPID_FIRE = SM5EventInfo(
        event_id=SM5_EVENT_ACTIVATE_RAPID_FIRE,
        name='ACTIVATE_RAPID_FIRE',
        description='Player activates rapid fire.',
    )
    DEACTIVATE_RAPID_FIRE = SM5EventInfo(
        event_id=SM5_EVENT_DEACTIVATE_RAPID_FIRE,
        name='DEACTIVATE_RAPID_FIRE',
        description='Player deactivates rapid fire.',
    )
    ACTIVATE_NUKE = SM5EventInfo(
        event_id=SM5_EVENT_ACTIVATE_NUKE,
        name='ACTIVATE_NUKE',
        description='Player activates nuke.',
    )
    DETONATE_NUKE = SM5EventInfo(
        event_id=SM5_EVENT_DETONATE_NUKE,
        name='DETONATE_NUKE',
        description='Player detonates nuke.',
    )
    RESUPPLY_AMMO = SM5EventInfo(
        event_id=SM5_EVENT_RESUPPLY_AMMO,
        name='RESUPPLY_AMMO',
        description='Player resupplies ammo to teammate.',
    )
    RESUPPLY_LIVES = SM5EventInfo(
        event_id=SM5_EVENT_RESUPPLY_LIVES,
        name='RESUPPLY_LIVES',
        description='Player resupplies lives to teammate.',
    )
    AMMO_BOOST = SM5EventInfo(
        event_id=SM5_EVENT_AMMO_BOOST,
        name='AMMO_BOOST',
        description='Player resupplies ammo to entire team.',
    )
    LIFE_BOOST = SM5EventInfo(
        event_id=SM5_EVENT_LIFE_BOOST,
        name='LIFE_BOOST',
        description='Player resupplies lives to entire team.',
    )
    PENALTY = SM5EventInfo(
        event_id=SM5_EVENT_PENALTY,
        name='PENALTY',
        description='Player receives a penalty from referee.',
    )
    ACHIEVEMENT = SM5EventInfo(
        event_id=SM5_EVENT_ACHIEVEMENT,
        name='ACHIEVEMENT',
        description='Player completes an achievement.',
    )
    REWARD = SM5EventInfo(
        event_id=SM5_EVENT_REWARD,
        name='REWARD',
        description='Player earns a reward.',
    )
    CLAIM_BEACON = SM5EventInfo(
        event_id=SM5_EVENT_CLAIM_BEACON,
        name='CLAIM_BEACON',
        description='Player claims a beacon.',
    )
    BASE_AWARDED = SM5EventInfo(
        event_id=SM5_EVENT_BASE_AWARDED,
        name='BASE_AWARDED',
        description='Player is awarded a base.',
    )
    NUKE_CANCEL = SM5EventInfo(
        event_id=SM5_EVENT_NUKE_CANCEL,
        name='NUKE_CANCEL',
        description='Nuke was canceled before detonation.',
    )

    def __init__(self, info: SM5EventInfo) -> None:
        """Initializes the SM5 event enum member.

        Args:
            info: Metadata describing the event.
        """
        self.event_id = info.event_id
        self.display_name = info.name
        self.description = info.description

    @classmethod
    def from_id(cls, event_id: str) -> 'SM5Event | None':
        """Retrieves an SM5 event enum by its TDF event ID.

        Args:
            event_id: The 4-digit hexadecimal event code string.

        Returns:
            SM5Event | None: The matching enum member, or None.

        Usage:
            event = SM5Event.from_id(SM5_EVENT_MISSILE_MISS)
        """
        norm_id = event_id.strip().upper()
        for member in cls:
            if member.event_id.upper() == norm_id:
                return member
        return None

    @classmethod
    def is_sm5_event(cls, event_id: str) -> bool:
        """Checks whether an event ID belongs to the SM5 event set.

        Args:
            event_id: The event ID code string.

        Returns:
            bool: True if event_id is an SM5 event, False otherwise.

        Usage:
            if SM5Event.is_sm5_event(event.event_type):
                pass
        """
        return cls.from_id(event_id) is not None
