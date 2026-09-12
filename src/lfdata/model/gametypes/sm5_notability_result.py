"""Result container for SM5 game notability and highlight tagline evaluation.

This module defines the Sm5NotabilityResult dataclass holding the matched
notability condition, generated tagline string, and evaluation metadata.

Usage example:
    from lfdata.model.gametypes.sm5_notability_result import (
        Sm5NotabilityResult,
    )

    result = Sm5NotabilityResult(
        condition=None,
        tagline='10K Scout game',
    )
"""

import dataclasses
from typing import Any

from lfdata.model.gametypes.sm5_notability_condition import (
    Sm5NotabilityCondition,
)


@dataclasses.dataclass(frozen=True)
class Sm5NotabilityResult:
    """Result container for SM5 game notability and highlight tagline.

    Attributes:
        condition: Matching Sm5NotabilityCondition, or None if not notable.
        tagline: Concise highlight tagline string (3-5 words).
        details: Dictionary containing evaluation context details.
    """

    condition: Sm5NotabilityCondition | None
    tagline: str
    details: dict[str, Any] = dataclasses.field(default_factory=dict)
