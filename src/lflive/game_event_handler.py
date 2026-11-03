"""Game event dispatcher for TDF record type 4 in lflive.

This module provides `GameEventHandler`, which coordinates event processing
by delegating to game-type specific handlers and managing mission lifecycles.

Usage example:
    from lflive.emitter import OutputEmitter
    from lflive.game_event_handler import GameEventHandler
    from lflive.state.game_state import LiveGameState

    state = LiveGameState()
    emitter = OutputEmitter()
    handler = GameEventHandler(game_state=state, emitter=emitter)
    handler.handle_event(time_ms=1000, code='0100', varies=[])
"""

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
from lfdata.model.gametypes.sm5_events import (
    SM5_EVENT_MISSION_END,
    SM5_EVENT_MISSION_START,
)
from lflive.constants import DATA_TYPE_EVENT_SCROLLER, DATA_TYPE_GAME_OVER
from lflive.emitter import OutputEmitter
from lflive.laserball_event_handler import LaserballEventHandler
from lflive.sm5_event_handler import SM5EventHandler
from lflive.state.game_state import LiveGameState


class GameEventHandler:
    """Dispatches TDF record type 4 events to game-type specific handlers.

    Attributes:
        game_state: Active LiveGameState container.
        emitter: Optional OutputEmitter broadcasting outbound events.
        laserball_handler: Specialized handler for Laserball events.
        sm5_handler: Specialized handler for Space Marines 5 events.
    """

    def __init__(
        self,
        game_state: LiveGameState,
        emitter: OutputEmitter | None = None,
    ) -> None:
        """Initializes the game event coordinator.

        Args:
            game_state: Active LiveGameState instance.
            emitter: Optional OutputEmitter instance.
        """
        self.game_state = game_state
        self.emitter = emitter
        self.laserball_handler = LaserballEventHandler(
            game_state=game_state,
            emitter=emitter,
        )
        self.sm5_handler = SM5EventHandler(
            game_state=game_state,
            emitter=emitter,
        )

    def handle_event(
        self,
        time_ms: int,
        code: str,
        varies: list[str],
    ) -> None:
        """Dispatches an incoming game event to the matching handler.

        Args:
            time_ms: Elapsed game time in milliseconds.
            code: 4-character event code string.
            varies: Variable event arguments.

        Usage example:
            handler.handle_event(1000, '0100', [])
        """
        if code in (SM5_EVENT_MISSION_START, SM5_EVENT_MISSION_END):
            self._handle_lifecycle(time_ms=time_ms, code=code)
        elif code in (
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
            self.laserball_handler.handle_event(
                time_ms=time_ms, code=code, varies=varies
            )
        else:
            self.sm5_handler.handle_event(
                time_ms=time_ms, code=code, varies=varies
            )

    def _handle_lifecycle(self, time_ms: int, code: str) -> None:
        """Handles mission start and mission end lifecycle events.

        Args:
            time_ms: Elapsed game time in milliseconds.
            code: Lifecycle event code.
        """
        if code == SM5_EVENT_MISSION_START:
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    '* Mission Start *',
                )
        elif code == SM5_EVENT_MISSION_END:
            self.game_state.is_game_over = True
            self.game_state.record_change(
                time_ms, 'game', 0, 'is_game_over', '1'
            )
            if self.emitter:
                self.emitter.emit(
                    DATA_TYPE_EVENT_SCROLLER,
                    time_ms,
                    '* Mission End *',
                )
                self.emitter.emit(DATA_TYPE_GAME_OVER, time_ms)
