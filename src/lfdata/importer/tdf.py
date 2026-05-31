"""TDF parser."""

from datetime import datetime
from pathlib import Path

from lfdata.model import (
    GameEntity,
    GameEvent,
    GameTeam,
    LFGame,
    Player,
    PlayerStateHistory,
    ScoreHistory,
    Sm5Stats,
)


class TdfImporter:
    """Importer and parser for TDF files."""

    def __init__(self, file_path: str | Path) -> None:
        """Initializes the TDF importer.

        Args:
            file_path: The file path to the TDF file.
        """
        self.file_path = Path(file_path)

    def _parse_line(self, line: str, game: LFGame) -> None:
        """Parses a single line of TDF data and updates the game object.

        Args:
            line: The raw text line to parse.
            game: The LFGame object to update.
        """
        line = line.strip()
        if not line or line.startswith(';'):
            return
        parts = line.split('\t')
        if not parts:
            return
        rec_type = parts[0]
        if rec_type == '0':
            self._parse_info(parts, game)
        elif rec_type == '1':
            self._parse_mission(parts, game)
        elif rec_type == '2':
            self._parse_team(parts, game)
        elif rec_type == '3':
            self._parse_entity_start(parts, game)
        elif rec_type == '4':
            self._parse_event(parts, game)
        elif rec_type == '5':
            self._parse_score(parts, game)
        elif rec_type == '6':
            self._parse_entity_end(parts, game)
        elif rec_type == '7':
            self._parse_sm5_stats(parts, game)
        elif rec_type == '9':
            self._parse_player_state(parts, game)

    def parse(self) -> LFGame:
        """Parses the TDF file and returns a LFGame data object.

        Returns:
            LFGame: The parsed LFGame object.

        Raises:
            FileNotFoundError: If the file is not found.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f'TDF file not found: {self.file_path}')

        game = LFGame(
            game_id=self.file_path.stem,
            timestamp=datetime.now(),
            game_type='Standard TDF',
        )

        try:
            with open(self.file_path, 'r', encoding='utf-16') as f:
                content = f.read()
        except UnicodeError:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

        for line in content.splitlines():
            self._parse_line(line, game)

        return game

    def _parse_info(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 0 (Info).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 4:
            game.file_version = parts[1]
            game.program_version = parts[2]
            game.centre = parts[3]

    def _parse_mission(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 1 (Mission).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 6:
            game.game_type = parts[2]
            if len(parts) >= 7:
                start_str = parts[4]
                duration_str = parts[5]
                penalty_str = parts[6]
            else:
                start_str = parts[3]
                duration_str = parts[4]
                penalty_str = parts[5]

            game.start = start_str
            try:
                game.timestamp = datetime.strptime(start_str, '%Y%m%d%H%M%S')
            except ValueError:
                pass
            try:
                game.duration = int(duration_str)
            except ValueError:
                pass
            try:
                game.penalty = int(penalty_str)
            except ValueError:
                pass

    def _parse_team(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 2 (Team).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 6:
            try:
                team_index = int(parts[1])
                color_enum = int(parts[3])
            except ValueError:
                return
            team = GameTeam(
                game_id=game.game_id,
                team_index=team_index,
                desc=parts[2],
                color_enum=color_enum,
                color_desc=parts[4],
                color_rgb=parts[5],
            )
            game.teams.append(team)

    def _parse_entity_start(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 3 (Entity-start).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 9:
            try:
                team_index = int(parts[5])
                level = int(parts[6])
                category = int(parts[7])
            except ValueError:
                return
            entity = GameEntity(
                game_id=game.game_id,
                entity_id=parts[2],
                type=parts[3],
                desc=parts[4],
                team_index=team_index,
                level=level,
                category=category,
                battlesuit=parts[8],
            )
            if entity.type == 'player':
                entity.player = Player(codename=entity.desc)
            game.entities.append(entity)

    def _parse_event(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 4 (Event).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 3:
            try:
                time_offset = int(parts[1])
            except ValueError:
                return
            event_type = parts[2]
            varies = parts[3:] if len(parts) > 3 else []
            actor_entity_id = None
            target_entity_id = None
            action = ''
            if len(varies) == 1:
                action = varies[0].strip()
            elif len(varies) == 2:
                actor_entity_id = varies[0]
                action = varies[1].strip()
            elif len(varies) >= 3:
                actor_entity_id = varies[0]
                action = varies[1].strip()
                target_entity_id = varies[2]
            event = GameEvent(
                game_id=game.game_id,
                time=time_offset,
                event_type=event_type,
                actor_entity_id=actor_entity_id,
                target_entity_id=target_entity_id,
                action=action,
                raw_message='\t'.join(varies),
            )
            game.events.append(event)

    def _parse_score(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 5 (Score).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 6:
            try:
                time_offset = int(parts[1])
                old_score = int(parts[3])
                delta_score = int(parts[4])
                new_score = int(parts[5])
            except ValueError:
                return
            score = ScoreHistory(
                game_id=game.game_id,
                time=time_offset,
                entity_id=parts[2],
                old_score=old_score,
                delta_score=delta_score,
                new_score=new_score,
            )
            game.score_history.append(score)

    def _parse_entity_end(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 6 (Entity-end).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 5:
            entity_id = parts[2]
            try:
                score = int(parts[4])
            except ValueError:
                return
            for entity in game.entities:
                if entity.entity_id == entity_id:
                    entity.end_score = score
                    break

    def _parse_sm5_stats(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 7 (SM5 Stats).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 25:
            try:
                stats = Sm5Stats(
                    game_id=game.game_id,
                    entity_id=parts[1],
                    shots_hit=int(parts[2]),
                    shots_fired=int(parts[3]),
                    times_zapped=int(parts[4]),
                    times_missiled=int(parts[5]),
                    missile_hits=int(parts[6]),
                    nukes_detonated=int(parts[7]),
                    nukes_activated=int(parts[8]),
                    nuke_cancels=int(parts[9]),
                    medic_hits=int(parts[10]),
                    own_medic_hits=int(parts[11]),
                    medic_nukes=int(parts[12]),
                    scout_rapid=int(parts[13]),
                    life_boost=int(parts[14]),
                    ammo_boost=int(parts[15]),
                    lives_left=int(parts[16]),
                    shots_left=int(parts[17]),
                    penalties=int(parts[18]),
                    shot3_hit=int(parts[19]),
                    own_nuke_cancels=int(parts[20]),
                    shot_opponent=int(parts[21]),
                    shot_team=int(parts[22]),
                    missiled_opponent=int(parts[23]),
                    missiled_team=int(parts[24]),
                )
                game.sm5_stats.append(stats)
            except ValueError:
                return

    def _parse_player_state(self, parts: list[str], game: LFGame) -> None:
        """Parses record type 9 (Player state).

        Args:
            parts: The fields of the row.
            game: The game object to update.
        """
        if len(parts) >= 4:
            try:
                time_offset = int(parts[1])
                state_val = int(parts[3])
            except ValueError:
                return
            state = PlayerStateHistory(
                game_id=game.game_id,
                time=time_offset,
                entity_id=parts[2],
                state=state_val,
            )
            game.state_history.append(state)
