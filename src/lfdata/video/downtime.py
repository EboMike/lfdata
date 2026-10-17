"""Player downtime timing analysis and asset adjustments.

This module provides classes and functions to scan TDF player state history
(type 9 records) for player downtime incidents, measure average total downtime
and time to become resettable, and generate dynamically adjusted downtime
assets when the resettable percentage deviates from standard configurations.

Usage example:
    from lfdata.model import LFGame
    from lfdata.video.downtime import DowntimeAnalyzer, adjust_downtime_asset

    analyzer = DowntimeAnalyzer()
    params = analyzer.analyze(game=game)
    print(f'Total downtime: {params.total_downtime_ms} ms')
"""

from collections import defaultdict
from dataclasses import dataclass, field

from PIL import Image

from lfdata.model import LFGame, PlayerStateHistory
from lfdata.model.constants.tdf import LFPlayerState


@dataclass
class DowntimeIncident:
    """Represents a validated single player downtime incident.

    Attributes:
        entity_id: Player entity ID string.
        down_time_ms: Millisecond timestamp when the player went down.
        resettable_time_ms: Millisecond timestamp when player became resettable.
        up_time_ms: Millisecond timestamp when the player returned upright.
        total_downtime_ms: Duration in milliseconds from down to up.
        time_to_resettable_ms: Duration in milliseconds from down to resettable.
    """

    entity_id: str
    down_time_ms: int
    resettable_time_ms: int
    up_time_ms: int
    total_downtime_ms: int = 0
    time_to_resettable_ms: int = 0

    def __post_init__(self) -> None:
        """Calculates duration fields if not provided."""
        if not self.total_downtime_ms:
            self.total_downtime_ms = self.up_time_ms - self.down_time_ms
        if not self.time_to_resettable_ms:
            self.time_to_resettable_ms = (
                self.resettable_time_ms - self.down_time_ms
            )


@dataclass
class DowntimeParameters:
    """Computed or default downtime timing parameters.

    Attributes:
        total_downtime_ms: Total duration of downtime in milliseconds.
        time_to_resettable_ms: Duration until player becomes resettable in ms.
        resettable_percentage: Fraction of total downtime before resettable.
        incidents: List of scanned DowntimeIncident objects used.
    """

    total_downtime_ms: int = 8000
    time_to_resettable_ms: int = 4000
    resettable_percentage: float = 0.5
    incidents: list[DowntimeIncident] = field(default_factory=list)


class DowntimeAnalyzer:
    """Analyzes game state history to compute player downtime parameters.

    Scans TDF type 9 records for valid downtime transitions (state 0 -> 3 -> 2
    -> 0) and averages up to 5 distinct incidents across the game.
    """

    def analyze(
        self,
        game: LFGame,
        max_incidents: int = 5,
    ) -> DowntimeParameters:
        """Scans game state history and returns calculated downtime parameters.

        Args:
            game: The LFGame data model instance.
            max_incidents: Maximum number of incidents to scan and average.

        Returns:
            DowntimeParameters: The measured or default downtime parameters.

        Raises:
            ValueError: If max_incidents is less than 1.
        """
        if max_incidents < 1:
            raise ValueError('max_incidents must be at least 1.')

        if not game.state_history:
            return DowntimeParameters()

        all_incidents = self._collect_incidents(game.state_history)
        if not all_incidents:
            return DowntimeParameters()

        all_incidents.sort(key=lambda inc: inc.down_time_ms)
        selected = all_incidents[:max_incidents]

        avg_total = sum(i.total_downtime_ms for i in selected) / len(selected)
        avg_resettable = sum(i.time_to_resettable_ms for i in selected) / len(
            selected
        )

        total_ms = round(avg_total)
        resettable_ms = round(avg_resettable)
        percentage = (avg_resettable / avg_total) if avg_total > 0 else 0.5

        return DowntimeParameters(
            total_downtime_ms=total_ms,
            time_to_resettable_ms=resettable_ms,
            resettable_percentage=percentage,
            incidents=selected,
        )

    def _collect_incidents(
        self,
        state_history: list[PlayerStateHistory],
    ) -> list[DowntimeIncident]:
        """Collects valid downtime incidents grouped per player entity.

        Args:
            state_history: List of PlayerStateHistory records.

        Returns:
            list[DowntimeIncident]: List of all valid incidents found.
        """
        records_by_entity: dict[str, list[PlayerStateHistory]] = defaultdict(
            list
        )
        for record in state_history:
            records_by_entity[record.entity_id].append(record)

        incidents: list[DowntimeIncident] = []
        for entity_id, records in records_by_entity.items():
            records.sort(key=lambda r: r.time)
            incidents.extend(
                self._scan_player_incidents(
                    entity_id=entity_id,
                    records=records,
                )
            )
        return incidents

    def _scan_player_incidents(
        self,
        entity_id: str,
        records: list[PlayerStateHistory],
    ) -> list[DowntimeIncident]:
        """Scans state transitions for a single player to find valid incidents.

        A valid incident transitions strictly from state 0 (UP) to state 3
        (DOWN), then to state 2 (RESETTABLE), then to state 0 (UP).

        Args:
            entity_id: Player entity ID string.
            records: Chronologically sorted state history records for player.

        Returns:
            list[DowntimeIncident]: List of valid downtime incidents for player.
        """
        incidents: list[DowntimeIncident] = []
        current_state: int = LFPlayerState.UP
        down_time_ms: int | None = None
        resettable_time_ms: int | None = None

        for rec in records:
            if current_state == LFPlayerState.UP:
                if rec.state == LFPlayerState.UP:
                    continue
                if rec.state == LFPlayerState.DOWN:
                    current_state = LFPlayerState.DOWN
                    down_time_ms = rec.time
                    resettable_time_ms = None
                else:
                    current_state = rec.state
                    down_time_ms = None
                    resettable_time_ms = None
            elif current_state == LFPlayerState.DOWN:
                if (
                    rec.state == LFPlayerState.RESETTABLE
                    and down_time_ms is not None
                    and rec.time > down_time_ms
                ):
                    current_state = LFPlayerState.RESETTABLE
                    resettable_time_ms = rec.time
                else:
                    current_state = rec.state
                    down_time_ms = None
                    resettable_time_ms = None
            elif current_state == LFPlayerState.RESETTABLE:
                if (
                    rec.state == LFPlayerState.UP
                    and down_time_ms is not None
                    and resettable_time_ms is not None
                    and rec.time > resettable_time_ms
                ):
                    incidents.append(
                        DowntimeIncident(
                            entity_id=entity_id,
                            down_time_ms=down_time_ms,
                            resettable_time_ms=resettable_time_ms,
                            up_time_ms=rec.time,
                        )
                    )
                    current_state = LFPlayerState.UP
                    down_time_ms = None
                    resettable_time_ms = None
                else:
                    current_state = rec.state
                    down_time_ms = None
                    resettable_time_ms = None

        return incidents


def adjust_downtime_asset(
    original_image: Image.Image,
    resettable_percentage: float,
    threshold: float = 0.02,
) -> Image.Image:
    """Adjusts the downtime-full asset to reflect non-standard resettable ratios.

    If the computed resettable percentage is significantly different than 50%
    (differing by more than threshold), the left half of the image is squeezed
    into the left percentage portion, and the right half is stretched into the
    remaining portion. Otherwise, original_image is returned.

    Args:
        original_image: The source Pillow Image of downtime-full.png.
        resettable_percentage: Fraction of total downtime before resettable.
        threshold: The threshold difference from 0.5 to trigger adjustment.

    Returns:
        Image.Image: The adjusted Image or the original Image.

    Raises:
        ValueError: If resettable_percentage is not between 0.0 and 1.0.
    """
    if not 0.0 <= resettable_percentage <= 1.0:
        raise ValueError('resettable_percentage must be between 0.0 and 1.0.')

    if abs(resettable_percentage - 0.5) <= threshold:
        return original_image

    width, height = original_image.size
    half_width = width // 2

    target_left_width = round(width * resettable_percentage)
    target_left_width = max(1, min(width - 1, target_left_width))
    target_right_width = width - target_left_width

    left_half = original_image.crop((0, 0, half_width, height))
    right_half = original_image.crop((half_width, 0, width, height))

    try:
        left_resized = left_half.resize(
            (target_left_width, height), Image.Resampling.LANCZOS
        )
        try:
            right_resized = right_half.resize(
                (target_right_width, height), Image.Resampling.LANCZOS
            )
            try:
                new_image = Image.new('RGBA', (width, height))
                new_image.paste(left_resized, (0, 0))
                new_image.paste(right_resized, (target_left_width, 0))
                return new_image
            finally:
                right_resized.close()
        finally:
            left_resized.close()
    finally:
        left_half.close()
        right_half.close()
