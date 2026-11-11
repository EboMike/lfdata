"""Data class representing basic competition metadata.

This module provides the CompetitionInfo dataclass, holding the name and unique
slug identifier of an LFstats competition.

Usage example:
    from lfdata.lfstats.competition_info import CompetitionInfo

    info = CompetitionInfo(
        name='Internationals 2026',
        slug='internationals_2026',
    )
    print(info.name, info.slug)
"""

from __future__ import annotations

import dataclasses
from typing import Iterator


@dataclasses.dataclass(frozen=True)
class CompetitionInfo:
    """Basic metadata describing an LFstats competition.

    Attributes:
        name: Human-readable display name of the competition.
        slug: Unique URL/API slug identifier of the competition.
    """

    name: str
    slug: str

    def __iter__(self) -> Iterator[str]:
        """Allows unpacking as (name, slug).

        Returns:
            Iterator[str]: Iterator yielding name then slug.

        Usage example:
            name, slug = comp_info
        """
        yield self.name
        yield self.slug

    def __getitem__(self, key: str) -> str:
        """Allows dictionary-style key access by 'name' or 'slug'.

        Args:
            key: Field name string ('name' or 'slug').

        Returns:
            str: Value of the requested field.

        Raises:
            KeyError: If key is not 'name' or 'slug'.

        Usage example:
            name = comp_info['name']
        """
        if key == 'name':
            return self.name
        if key == 'slug':
            return self.slug
        raise KeyError(f"Invalid field: '{key}', expected 'name' or 'slug'.")

