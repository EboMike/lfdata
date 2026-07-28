"""Chapter generator for LF games.

Generates a list of chapters for a TDF playback dataset, filtering and
consolidating them into a YouTube chapter list format.
"""

import dataclasses
from lfdata.model import LFGame, LFRole
from lfdata.replay import LFReplaySystem


@dataclasses.dataclass
class LFChapter:
    """Represents a chapter marker in a game timeline.

    Attributes:
        time_ms: The millisecond timestamp since the beginning of the game.
        message: The text of the event that triggered the chapter.
        importance: The importance level of this chapter (higher is more
          important, from 1 to 5).
    """

    time_ms: int
    message: str
    importance: int


class LFChapterGenerator:
    """Generates and filters chapter markers for a game playback."""

    def __init__(self, game: LFGame) -> None:
        """Initializes the chapter generator.

        Args:
            game: The LFGame object containing game events and entities.
        """
        self.game = game

    def generate(self) -> list[LFChapter]:
        """Runs replay simulation to collect and filter candidate chapters.

        Calculates transitions and events, applies the 10-second filtering
        and consolidation rules, and limits the list to at most 20 chapters.

        Returns:
            list[LFChapter]: The list of filtered chapter markers.
        """
        candidates = self._collect_candidates()
        consolidated = self._filter_and_consolidate(candidates)
        return self._limit_chapters(consolidated, max_chapters=20)

    def format_youtube_chapters(
        self,
        chapters: list[LFChapter],
        pregame_delay_ms: int = 0,
    ) -> str:
        """Formats the list of chapters as a YouTube chapter string.

        Args:
            chapters: The list of chapter markers.
            pregame_delay_ms: Pregame delay in milliseconds to add to
              timestamps.

        Returns:
            str: The YouTube chapter string format.
        """
        sorted_ch = sorted(chapters, key=lambda c: c.time_ms)
        has_zero = False
        ch_entries = []

        for ch in sorted_ch:
            v_time_ms = ch.time_ms + pregame_delay_ms
            if v_time_ms <= 0:
                has_zero = True
            ch_entries.append((v_time_ms, ch.message))

        if not has_zero:
            first_name = (
                'Game Start' if pregame_delay_ms == 0 else 'Getting Ready'
            )
            ch_entries.insert(0, (0, first_name))

        if pregame_delay_ms > 20000:
            has_game_start = any(msg == 'Game Start' for _, msg in ch_entries)
            if not has_game_start:
                inserted = False
                for idx, (t, _) in enumerate(ch_entries):
                    if t >= pregame_delay_ms:
                        ch_entries.insert(
                            idx, (pregame_delay_ms, 'Game Start')
                        )
                        inserted = True
                        break
                if not inserted:
                    ch_entries.append((pregame_delay_ms, 'Game Start'))

        # Check final 20 chapters limit and truncate if necessary
        if len(ch_entries) > 20:
            # We want to remove the lowest importance ones.
            # Structural chapters (00:00 start / game start) are kept.
            num_structural = len(ch_entries) - len(sorted_ch)
            limit = max(1, 20 - num_structural)
            limited_original = self._limit_chapters(
                chapters, max_chapters=limit
            )
            return self.format_youtube_chapters(
                limited_original,
                pregame_delay_ms=pregame_delay_ms,
            )

        formatted_lines = []
        for v_time_ms, msg in ch_entries:
            total_sec = max(0, v_time_ms // 1000)
            mins = total_sec // 60
            secs = total_sec % 60
            formatted_lines.append(f'{mins:02d}:{secs:02d} {msg}')

        return '\n'.join(formatted_lines)

    def _collect_candidates(self) -> list[LFChapter]:
        """Collects all initial chapter candidates from game playback.

        Returns:
            list[LFChapter]: Collected initial chapter candidates.
        """
        candidates: list[LFChapter] = []
        replay = LFReplaySystem(self.game)
        sorted_events = sorted(self.game.events, key=lambda e: e.time)

        # Pre-populate initial player roles and lives
        lives_before = {
            pid: p.lives for pid, p in replay.game_state.players.items()
        }

        # Track nuke detonate events separately along with any team eliminations
        nuke_detonations: list[tuple[GameEvent, str, list[str]]] = []

        for event in sorted_events:
            for player in replay.game_state.players.values():
                player.update_downtime(event.time)

            lives_before = {
                pid: p.lives for pid, p in replay.game_state.players.items()
            }

            active_teams_before = {
                t_idx: any(
                    p.lives > 0
                    for p in replay.game_state.players.values()
                    if p.team_index == t_idx
                )
                for t_idx in replay.game_state.teams
            }

            description = replay._dispatch_event(event)
            replay.game_state.update_team_scores_and_rankings()

            active_teams_after = {
                t_idx: any(
                    p.lives > 0
                    for p in replay.game_state.players.values()
                    if p.team_index == t_idx
                )
                for t_idx in replay.game_state.teams
            }

            newly_eliminated_teams = [
                replay.game_state.teams[t_idx].name
                for t_idx in replay.game_state.teams
                if active_teams_before.get(t_idx, False)
                and not active_teams_after.get(t_idx, False)
            ]
            team_elim_str = ''.join(
                f', {self._get_team_short_name(t_name)} team eliminated'
                for t_name in newly_eliminated_teams
            )

            # 1. Check player state changes
            for pid, player in replay.game_state.players.items():
                old_lives = lives_before.get(pid, 0)
                new_lives = player.lives
                p_name = replay.entity_names.get(pid, pid)

                if old_lives > 0 and new_lives == 0:
                    if player.role == LFRole.MEDIC:
                        candidates.append(
                            LFChapter(
                                time_ms=event.time,
                                message=f'{p_name} eliminated{team_elim_str}',
                                importance=5,
                            )
                        )
                    elif player.role == LFRole.COMMANDER:
                        candidates.append(
                            LFChapter(
                                time_ms=event.time,
                                message=f'{p_name} eliminated{team_elim_str}',
                                importance=4,
                            )
                        )
                    else:
                        candidates.append(
                            LFChapter(
                                time_ms=event.time,
                                message=f'{p_name} eliminated{team_elim_str}',
                                importance=2,
                            )
                        )
                elif (
                    player.role == LFRole.MEDIC
                    and old_lives > 10
                    and 0 < new_lives <= 10
                ):
                    candidates.append(
                        LFChapter(
                            time_ms=event.time,
                            message=f'Medic {p_name} has {new_lives} lives left{team_elim_str}',
                            importance=1,
                        )
                    )

            # 2. Check nuke events
            if event.event_type == 'nuke_cancel':
                candidates.append(
                    LFChapter(
                        time_ms=event.time,
                        message=f'{description}{team_elim_str}',
                        importance=3,
                    )
                )
            elif event.event_type == '0405':
                nuke_detonations.append(
                    (event, description, newly_eliminated_teams)
                )

        # Group and process nuke detonations by commander
        detonations_by_actor: dict[
            str, list[tuple[GameEvent, str, list[str]]]
        ] = {}
        for ev, desc, elim_teams in nuke_detonations:
            actor_id = ev.actor_entity_id
            if not actor_id:
                team_elim_str = ''.join(
                    f', {self._get_team_short_name(t_name)} team eliminated'
                    for t_name in elim_teams
                )
                candidates.append(
                    LFChapter(
                        time_ms=ev.time,
                        message=f'{desc}{team_elim_str}',
                        importance=3,
                    )
                )
                continue
            detonations_by_actor.setdefault(actor_id, []).append(
                (ev, desc, elim_teams)
            )

        for actor_id, evs in detonations_by_actor.items():
            sorted_evs = sorted(evs, key=lambda x: x[0].time)
            sequences: list[list[tuple[GameEvent, str, list[str]]]] = []
            current_seq: list[tuple[GameEvent, str, list[str]]] = []
            for ev, desc, elim_teams in sorted_evs:
                if not current_seq:
                    current_seq.append((ev, desc, elim_teams))
                else:
                    prev_ev, _, _ = current_seq[-1]
                    if ev.time - prev_ev.time <= 15000:
                        current_seq.append((ev, desc, elim_teams))
                    else:
                        sequences.append(current_seq)
                        current_seq = [(ev, desc, elim_teams)]
            if current_seq:
                sequences.append(current_seq)

            for seq in sequences:
                seq_elim_teams: list[str] = []
                for _, _, elim_teams in seq:
                    for t_name in elim_teams:
                        if t_name not in seq_elim_teams:
                            seq_elim_teams.append(t_name)
                team_elim_str = ''.join(
                    f', {self._get_team_short_name(t_name)} team eliminated'
                    for t_name in seq_elim_teams
                )

                if len(seq) == 1:
                    ev, desc, _ = seq[0]
                    candidates.append(
                        LFChapter(
                            time_ms=ev.time,
                            message=f'{desc}{team_elim_str}',
                            importance=3,
                        )
                    )
                else:
                    first_ev, _, _ = seq[0]
                    actor_name = replay.entity_names.get(actor_id, actor_id)
                    suffix = self._get_multi_nuke_suffix(len(seq))
                    msg = f'Commander {actor_name} {suffix}{team_elim_str}'
                    candidates.append(
                        LFChapter(
                            time_ms=first_ev.time,
                            message=msg,
                            importance=3,
                        )
                    )

        return candidates

    def _get_team_short_name(self, name: str) -> str:
        """Returns the short team name without 'Team' suffix if present.

        Args:
            name: The full team name.

        Returns:
            str: The short team name.
        """
        if name.endswith(' Team'):
            return name[:-5]
        return name

    def _get_multi_nuke_suffix(self, count: int) -> str:
        """Returns the suffix for multiple nuke detonations.

        Args:
            count: The number of nukes detonated.

        Returns:
            str: The multi-nuke description suffix.
        """
        nuke_count_names = {
            2: 'double-nukes',
            3: 'triple-nukes',
            4: 'quad-nukes',
            5: 'penta-nukes',
            6: 'hexa-nukes',
            7: 'hepta-nukes',
            8: 'octa-nukes',
        }
        return nuke_count_names.get(count, f'{count}-nukes')

    def _filter_and_consolidate(
        self, chapters: list[LFChapter]
    ) -> list[LFChapter]:
        """Filters and consolidates chapters using the 10-second rule.

        Args:
            chapters: List of initial candidate chapters.

        Returns:
            list[LFChapter]: The filtered and consolidated chapters.
        """
        current = sorted(chapters, key=lambda c: c.time_ms)

        while True:
            conflict_found = False
            for i in range(len(current) - 1):
                c1 = current[i]
                c2 = current[i + 1]

                if abs(c1.time_ms - c2.time_ms) <= 10000:
                    conflict_found = True
                    if c1.importance != c2.importance:
                        if c1.importance < c2.importance:
                            current.pop(i)
                        else:
                            current.pop(i + 1)
                    else:
                        combined_msg = f'{c1.message}, {c2.message}'
                        combined_ch = LFChapter(
                            time_ms=min(c1.time_ms, c2.time_ms),
                            message=combined_msg,
                            importance=c1.importance,
                        )
                        current[i] = combined_ch
                        current.pop(i + 1)
                    break
            if not conflict_found:
                break

        return current

    def _limit_chapters(
        self, chapters: list[LFChapter], max_chapters: int = 20
    ) -> list[LFChapter]:
        """Limits the total number of chapters to max_chapters.

        Args:
            chapters: List of chapters to limit.
            max_chapters: Maximum allowed number of chapters.

        Returns:
            list[LFChapter]: The limited list of chapters.
        """
        if len(chapters) <= max_chapters:
            return chapters

        elim_sorted = sorted(chapters, key=lambda c: (c.importance, -c.time_ms))
        num_to_eliminate = len(chapters) - max_chapters
        kept_chapters = elim_sorted[num_to_eliminate:]
        return sorted(kept_chapters, key=lambda c: c.time_ms)
