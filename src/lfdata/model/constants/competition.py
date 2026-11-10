"""Enums and constants representing competition formats and stages.

This module defines stage types (games, halves, overtime) used in competition
schedules, stage type indicators, and formatting helpers.

Usage example:
    from lfdata.model.constants.competition import StageType

    stage = StageType.from_code('H')
    print(f'Stage: {stage.display_name} ({stage.code})')
"""

import enum

DEFAULT_STAGE_INDICATOR: str = 'G'
STAGE_CODE_GAME: str = 'G'
STAGE_CODE_HALF: str = 'H'
STAGE_CODE_OVERTIME: str = 'OT'


class StageType(enum.Enum):
    """Enumeration of competition game stages or halves.

    Attributes:
        code: Short code string representing the stage (e.g. 'G', 'H', 'OT').
        display_name: Human-readable display name for the stage.
    """

    GAME = (STAGE_CODE_GAME, 'Game')
    HALF = (STAGE_CODE_HALF, 'Half')
    OVERTIME = (STAGE_CODE_OVERTIME, 'Overtime')

    def __init__(self, code: str, display_name: str) -> None:
        """Initializes the stage type enum member.

        Args:
            code: Short code identifier for the stage.
            display_name: Human-readable display name.
        """
        self.code = code
        self.display_name = display_name

    @classmethod
    def from_code(cls, code: str) -> 'StageType':
        """Retrieves a stage type by its short code.

        Args:
            code: The stage code string (e.g. 'G', 'H', 'OT').

        Returns:
            StageType: The matching stage type enum member.

        Raises:
            ValueError: If the stage code is not recognized.

        Usage example:
            stage = StageType.from_code('OT')
        """
        upper_code = code.upper()
        for member in cls:
            if member.code == upper_code:
                return member
        raise ValueError(f'Invalid stage code: {code}')

