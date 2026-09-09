# Additional Context

## Hit Differential (Hit Diff)

In all game modes, a player has an accessor for their "hit diff".
The hit diff is defined as:
hit_diff = (hits against players on other teams) / (times player got zapped)

Rules:
* It only includes hits against players in other teams. It does not include
  own teams (friendly fire), or bases.
* Missiles or nukes do not factor into this equation.
* If a player was never zapped (times zapped is 0), the hit diff is 1.
* In SM5, this corresponds to `shot_opponent / times_zapped`.
* Accessible via `hit_diff` property on player game mode stats (e.g.
  `Sm5Stats.hit_diff`), on `GameEntity.hit_diff`, and on
  `LFReplayPlayerState.hit_diff`.

## Audio File Validation and Error Handling

* `tune-audio` and `match-audio` must immediately raise an exception if any
  referenced file does not exist (e.g. `FileNotFoundError`) or fails to be
  decoded and analyzed (e.g. `RuntimeError` or `ValueError`).
* Missing test case videos or reference sound files in sound definition YAML
  configurations must not be swallowed or treated as benchmark test failures;
  they must abort execution immediately.

