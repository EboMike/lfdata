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


def parse_competitions_list(raw_data: object) -> list[CompetitionInfo]:
    """Parses raw competitions API response into a list of CompetitionInfo.

    Args:
        raw_data: Raw JSON response object (dict with 'data' key or list).

    Returns:
        list[CompetitionInfo]: List of parsed CompetitionInfo objects.

    Raises:
        ValueError: If raw_data format is invalid.

    Usage example:
        comps = parse_competitions_list(raw_json)
    """
    if isinstance(raw_data, dict):
        items = raw_data.get('data')
        if not isinstance(items, list):
            raise ValueError(
                f"Expected 'data' field to be a list, got {type(items)}."
            )
    elif isinstance(raw_data, list):
        items = raw_data
    else:
        raise ValueError(
            'Expected competitions response to be a dict or list, got '
            f'{type(raw_data)}.'
        )

    results: list[CompetitionInfo] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get('name', ''))
        slug = str(item.get('slug', ''))
        if name or slug:
            results.append(CompetitionInfo(name=name, slug=slug))
    return results

