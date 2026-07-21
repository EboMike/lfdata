from unittest.mock import MagicMock, patch
from lfdata.model import GameEntity, LFGame, Sm5Stats
from lfdata.replay.verification import LFReplayVerifier, PlayerDiscrepancy


def test_player_discrepancy_dataclass() -> None:
    disc = PlayerDiscrepancy(field='score', computed=1000, expected=1500)
    assert disc.field == 'score'
    assert disc.computed == 1000
    assert disc.expected == 1500


def test_verifier_no_discrepancies() -> None:
    game = LFGame(game_id='test_verify_game', game_type='SM5')

    entity = GameEntity(
        game_id='test_verify_game',
        entity_id='player_1',
        type='player',
        desc='PlayerOne',
        team_index=1,
        end_score=1000,
    )
    game.entities = [entity]

    stats = Sm5Stats(
        game_id='test_verify_game',
        entity_id='player_1',
        lives_left=15,
        shots_left=30,
    )
    game.sm5_stats = [stats]

    verifier = LFReplayVerifier(game)

    mock_replay = MagicMock()
    mock_player_state = MagicMock()
    mock_player_state.score = 1000
    mock_player_state.lives = 15
    mock_player_state.shots = 30
    mock_replay.game_state.players = {'player_1': mock_player_state}

    discrepancies = verifier.get_discrepancies(mock_replay)
    assert len(discrepancies) == 0

    with patch(
        'lfdata.replay.verification.LFReplaySystem'
    ) as mock_replay_class:
        mock_replay_inst = MagicMock()
        mock_replay_inst.game_state.players = {'player_1': mock_player_state}
        mock_replay_class.return_value = mock_replay_inst

        assert verifier.verify() is True


def test_verifier_with_discrepancies_resolved() -> None:
    game = LFGame(game_id='test_verify_game', game_type='SM5')

    entity = GameEntity(
        game_id='test_verify_game',
        entity_id='player_1',
        type='player',
        desc='PlayerOne',
        team_index=1,
        end_score=1000,
    )
    game.entities = [entity]

    stats = Sm5Stats(
        game_id='test_verify_game',
        entity_id='player_1',
        lives_left=15,
        shots_left=30,
    )
    game.sm5_stats = [stats]

    verifier = LFReplayVerifier(game)

    mock_player_state_discrepant = MagicMock()
    mock_player_state_discrepant.score = 800
    mock_player_state_discrepant.lives = 10
    mock_player_state_discrepant.shots = 25

    mock_replay_no_align = MagicMock()
    mock_replay_no_align.game_state.players = {
        'player_1': mock_player_state_discrepant
    }

    discrepancies = verifier.get_discrepancies(mock_replay_no_align)
    assert len(discrepancies) == 1
    assert len(discrepancies['player_1']) == 3

    fields = {d.field: d for d in discrepancies['player_1']}
    assert fields['score'].computed == 800
    assert fields['score'].expected == 1000
    assert fields['lives'].computed == 10
    assert fields['lives'].expected == 15
    assert fields['shots'].computed == 25
    assert fields['shots'].expected == 30

    mock_player_state_aligned = MagicMock()
    mock_player_state_aligned.score = 1000
    mock_player_state_aligned.lives = 15
    mock_player_state_aligned.shots = 30

    with patch(
        'lfdata.replay.verification.LFReplaySystem'
    ) as mock_replay_class:
        mock_inst_no_align = MagicMock()
        mock_inst_no_align.game_state.players = {
            'player_1': mock_player_state_discrepant
        }

        mock_inst_aligned = MagicMock()
        mock_inst_aligned.game_state.players = {
            'player_1': mock_player_state_aligned
        }
        mock_inst_aligned.resolved_ambiguities = [
            {
                'time_ms': 5000,
                'player_id': 'player_1',
                'default': False,
                'chosen': True,
                'event_type': '0512',
            }
        ]
        mock_inst_aligned.entity_names = {'player_1': 'PlayerOne'}

        mock_replay_class.side_effect = [mock_inst_no_align, mock_inst_aligned]

        assert verifier.verify() is False
