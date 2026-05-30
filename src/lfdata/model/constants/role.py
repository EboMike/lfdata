"""Enums representing LF player roles and metadata."""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True)
class LFRoleStats:
    """Statistics and metadata for a player role.

    Attributes:
        role_id: The category ID from TDF files.
        display_name: The printable name of the role.
        start_lives: The initial lives count.
        start_shots: The initial shots count.
        start_missiles: The initial missiles count.
        max_lives: The maximum limit of lives.
        max_shots: The maximum limit of shots.
        medic_lives_gain: Lives gained when zapped by a medic.
        ammo_shots_gain: Shots gained when zapped by an ammo carrier.
        max_hp: The maximum hit points (shields) for the role.
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
    """Defines roles in LF SM5 games, including metadata stats.

    Metadata includes startup lives, shots, missiles, and resupply rates.
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
        max_hp=2,
    )
    AMMO = LFRoleStats(
        role_id=4,
        display_name='Ammo',
        start_lives=10,
        start_shots=0,
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
