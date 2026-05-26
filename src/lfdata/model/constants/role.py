"""Enums representing LF player roles and metadata."""

import enum


class LFRole(enum.Enum):
    """Defines roles in LF SM5 games, including metadata stats.

    Metadata includes startup lives, shots, missiles, and resupply rates.
    """

    COMMANDER = (1, "Commander", 15, 30, 5, 30, 60, 4, 5, 3)
    HEAVY = (2, "Heavy", 10, 20, 5, 20, 40, 3, 5, 3)
    SCOUT = (3, "Scout", 15, 30, 0, 30, 60, 3, 10, 1)
    MEDIC = (5, "Medic", 20, 15, 0, 20, 20, 0, 5, 2)
    AMMO = (4, "Ammo", 10, 0, 0, 20, 0, 3, 0, 1)

    def __init__(
        self,
        role_id: int,
        display_name: str,
        start_lives: int,
        start_shots: int,
        start_missiles: int,
        max_lives: int,
        max_shots: int,
        medic_lives_gain: int,
        ammo_shots_gain: int,
        max_hp: int,
    ):
        """Initializes the role with game balancing parameters.

        Args:
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
        self.role_id = role_id
        self.display_name = display_name
        self.start_lives = start_lives
        self.start_shots = start_shots
        self.start_missiles = start_missiles
        self.max_lives = max_lives
        self.max_shots = max_shots
        self.medic_lives_gain = medic_lives_gain
        self.ammo_shots_gain = ammo_shots_gain
        self.max_hp = max_hp

    @classmethod
    def from_id(cls, role_id: int) -> "LFRole":
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
        raise ValueError(f"Invalid role ID: {role_id}")
