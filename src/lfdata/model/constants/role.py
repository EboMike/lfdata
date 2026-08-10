"""Enums representing LF player roles and metadata.

This module defines Space Marines 5 player roles (Commander, Heavy, Scout, Medic, Ammo),
their initial ammo/lives, maximum capacities, resupply rates, and shield hit points.

Usage example:
    from lfdata.model import LFRole

    role = LFRole.from_id(1)
    print(f'Role: {role.display_name}, Start Lives: {role.start_lives}')
"""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LFRoleStats:
    """Game statistics and balance parameters for a player role.

    Holds role ID, display name, starting/maximum lives and shots, missile count,
    resupply rates, and maximum hit points.
    """

    role_id: int
    display_name: str
    start_lives: int
    start_shots: int
    start_missiles: int
    max_lives: int
    max_shots: int
    medic_lives_gain: int
    ammo_shots_gain: int
    max_hp: int


class LFRole(enum.Enum):
    """Enumeration of player roles in Space Marines 5 games.

    Provides role lookup by TDF category ID and access to role balance parameters.
    """

    COMMANDER = LFRoleStats(
        role_id=1,
        display_name='Commander',
        start_lives=15,
        start_shots=30,
        start_missiles=5,
        max_lives=30,
        max_shots=60,
        medic_lives_gain=4,
        ammo_shots_gain=5,
        max_hp=3,
    )
    HEAVY = LFRoleStats(
        role_id=2,
        display_name='Heavy',
        start_lives=10,
        start_shots=20,
        start_missiles=5,
        max_lives=20,
        max_shots=40,
        medic_lives_gain=3,
        ammo_shots_gain=5,
        max_hp=3,
    )
    SCOUT = LFRoleStats(
        role_id=3,
        display_name='Scout',
        start_lives=15,
        start_shots=30,
        start_missiles=0,
        max_lives=30,
        max_shots=60,
        medic_lives_gain=5,
        ammo_shots_gain=10,
        max_hp=1,
    )
    MEDIC = LFRoleStats(
        role_id=5,
        display_name='Medic',
        start_lives=20,
        start_shots=15,
        start_missiles=0,
        max_lives=20,
        max_shots=30,
        medic_lives_gain=0,
        ammo_shots_gain=5,
        max_hp=1,
    )
    AMMO = LFRoleStats(
        role_id=4,
        display_name='Ammo',
        start_lives=10,
        start_shots=15,
        start_missiles=0,
        max_lives=20,
        max_shots=0,
        medic_lives_gain=3,
        ammo_shots_gain=0,
        max_hp=1,
    )

    def __init__(self, stats: LFRoleStats) -> None:
        """Initializes the role with game balancing parameters.

        Args:
            stats: The role metadata statistics object.
        """
        self.role_id = stats.role_id
        self.display_name = stats.display_name
        self.start_lives = stats.start_lives
        self.start_shots = stats.start_shots
        self.start_missiles = stats.start_missiles
        self.max_lives = stats.max_lives
        self.max_shots = stats.max_shots
        self.medic_lives_gain = stats.medic_lives_gain
        self.ammo_shots_gain = stats.ammo_shots_gain
        self.max_hp = stats.max_hp

    @classmethod
    def from_id(cls, role_id: int) -> 'LFRole':
        """Retrieves a role by its TDF category ID.

        Args:
            role_id: The category ID integer.

        Returns:
            LFRole: The matching role enum.

        Raises:
            ValueError: If the role_id is not valid.
        """
        for role in cls:
            if role.role_id == role_id:
                return role
        raise ValueError(f'Invalid role ID: {role_id}')
