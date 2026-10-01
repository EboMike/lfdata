"""Constants and enums for TDF record types and player state codes.

This module defines string constants for TDF record types (0 through 9)
and integer enums for player operational states (up, down, resettable)
as reported in type 9 records.

Usage example:
    from lfdata.model.constants.tdf import TDF_RECORD_EVENT, LFPlayerState

    if record_type == TDF_RECORD_EVENT:
        print('Event record')
    if player_state == LFPlayerState.RESETTABLE:
        print('Player is resettable')
"""

import enum

# TDF record type identifiers (first column in TDF files)
TDF_RECORD_INFO: str = '0'
TDF_RECORD_MISSION: str = '1'
TDF_RECORD_TEAM: str = '2'
TDF_RECORD_ENTITY_START: str = '3'
TDF_RECORD_EVENT: str = '4'
TDF_RECORD_SCORE: str = '5'
TDF_RECORD_ENTITY_END: str = '6'
TDF_RECORD_STATS: str = '7'
TDF_RECORD_PLAYER_STATE: str = '9'


class LFPlayerState(enum.IntEnum):
    """Enumeration of player operational states in TDF type 9 records.

    Attributes:
        UP: Player is active and upright (state 0).
        RESETTABLE: Player is down and eligible to reset immediately (state 2).
        DOWN: Player is down in safe / non-resettable time (state 3).
    """

    UP = 0
    RESETTABLE = 2
    DOWN = 3
