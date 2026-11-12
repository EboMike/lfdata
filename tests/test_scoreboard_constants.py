from lfdata.model.constants.scoreboard import ScoreboardAdditionalValues


def test_scoreboard_additional_values_members() -> None:
    assert ScoreboardAdditionalValues.NEVER.value == 'never'
    assert ScoreboardAdditionalValues.AFTER_GAME.value == 'after_game'
    assert ScoreboardAdditionalValues.ALWAYS.value == 'always'


def test_scoreboard_additional_values_from_str() -> None:
    assert (
        ScoreboardAdditionalValues.from_str('never')
        == ScoreboardAdditionalValues.NEVER
    )
    assert (
        ScoreboardAdditionalValues.from_str('Never')
        == ScoreboardAdditionalValues.NEVER
    )
    assert (
        ScoreboardAdditionalValues.from_str('after_game')
        == ScoreboardAdditionalValues.AFTER_GAME
    )
    assert (
        ScoreboardAdditionalValues.from_str('After game')
        == ScoreboardAdditionalValues.AFTER_GAME
    )
    assert (
        ScoreboardAdditionalValues.from_str('after game')
        == ScoreboardAdditionalValues.AFTER_GAME
    )
    assert (
        ScoreboardAdditionalValues.from_str('always')
        == ScoreboardAdditionalValues.ALWAYS
    )
    assert (
        ScoreboardAdditionalValues.from_str('ALWAYS')
        == ScoreboardAdditionalValues.ALWAYS
    )


def test_scoreboard_additional_values_defaults() -> None:
    assert (
        ScoreboardAdditionalValues.from_str(None)
        == ScoreboardAdditionalValues.AFTER_GAME
    )
    assert (
        ScoreboardAdditionalValues.from_str('')
        == ScoreboardAdditionalValues.AFTER_GAME
    )
    assert (
        ScoreboardAdditionalValues.from_str('unknown_mode')
        == ScoreboardAdditionalValues.AFTER_GAME
    )

