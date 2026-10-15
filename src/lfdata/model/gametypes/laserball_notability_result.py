"""Result container for Laserball game notability and highlight tagline.

This module defines the LaserballNotabilityResult dataclass holding the matched
notability condition, generated tagline string, and evaluation metadata.

Usage example:
    from lfdata.model.gametypes.laserball_notability_result import (
        LaserballNotabilityResult,
    )

    result = LaserballNotabilityResult(
        condition=None,
        tagline='10/30 blocks',
    )
"""

from __future__ import annotations

import dataclasses

from lfdata.model.gametypes.laserball_notability_condition import (
    LaserballNotabilityCondition,
)


@dataclasses.dataclass(frozen=True)
class LaserballNotabilityResult:
    """Result container for Laserball game notability and highlight tagline.

    Attributes:
        condition: Matching LaserballNotabilityCondition, or None if not notable.
        tagline: Concise highlight tagline string (3-5 words).
        details: Dictionary containing evaluation context details.
    """

    condition: LaserballNotabilityCondition | None
    tagline: str
    details: dict[str, int | float | str] = dataclasses.field(
        default_factory=dict
    )
