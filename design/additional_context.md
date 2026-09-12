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

## SM5 Game Notability Conditions

SM5 notability conditions evaluate games in priority order:
1. `DRAW`: Game ended in a draw with identical scores.
2. `CLOSE_GAME`: Teams ended within 200 points of each other.
3. `COMMANDER_NUKES`: Focus player was a commander with > 5 nukes.
4. `HIGH_HIT_DIFF`: Focus player had a hit diff of 1.9 or more.
5. `HIGH_MEDIC_HITS`: Focus player had 9 or more medic hits.
6. `LONE_SURVIVOR_CRITICAL`: Focus player lone survivor with 1-2 lives left.
7. `LONE_SURVIVOR`: Focus player lone survivor with >= 3 lives left.
8. `FAST_TEAM_ELIMINATION`: Team was eliminated in less than 8 minutes.
9. `ALMOST_ELIMINATED_OPPONENTS`: Opponents had 1-5 combined lives left.
10. `MEDIC_ZAPPED_MEDIC`: Focus medic zapped enemy medic 3 or more times.
11. `NEVER_ZAPPED`: Focus player was never zapped (0 times).
12. `LOW_TIMES_ZAPPED`: Focus player was zapped less than 5 times.

