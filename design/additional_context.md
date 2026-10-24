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
* In Laserball, this corresponds to `(blocks + steals) / times_zapped`.
* Accessible via `hit_diff` property on player game mode stats (e.g.
  `Sm5Stats.hit_diff`, `LaserballStats.hit_diff`), on `GameEntity.hit_diff`, and
  on `LFReplayPlayerState.hit_diff`.

## Laserball Scoring and Team Rankings

* In Laserball, team score is the cumulative number of goals scored by that
  team (1 point per goal).
* Player score is used only for roster ranking:
  `score = (goals + assists) * 10000 + min(99, clears + steals) * 100`
  `+ min(99, blocks)` plus penalty points if applicable.
* Laserball players have unlimited lives and shots and are never eliminated.

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

## Event 0209 (Warbot Zap)

* Event 0209 corresponds to a warbot zap.
* The first entity is the entity of a warbot (a non-player entity), and the
  second entity is the player being zapped.
* There are no side effects to shots or lives.

## Event 0B00 (Claim Beacon)

* Event 0B00 corresponds to `<player> claims a beacon`.
* The acting player loses three shots. There are no other state or score
  effects.

## Penalty Player Event

* If the focus player receives a penalty (event `0600`), it is considered a
  player event: `"Received a penalty"`.
* A penalty immediately puts the player down for 8 seconds (4 seconds safe,
  4 seconds resettable), as if they were zapped with shield left (no lives
  lost).
* When rendering the animation for a player getting zapped (the border around
  the image / hit border), a yellow color is used if the player got penalized.

## SM5 Special Points Boost Costs

* Resupplying team members with lives (Medic boost) costs 10 special points.
* Resupplying team members with ammo (Ammo boost) costs 15 special points.

## Base Zap Replacement Window

* When the focus player zaps the same base multiple times within 8 seconds
  (8000 ms), each zap replaces the previous message instead of creating a
  new message:
  - First zap: `Zapped base <base name>`
  - Second zap: `2x Zapped base <base name>` (increments for subsequent hits)
  - Destroy zap: `Destroyed base <base name>` (if resulting in destruction)
* If more than 8 seconds elapse between zaps on that base, a new event entry
  is created.

## Laserball Chapter Markers

In Laserball, chapter markers are generated from goal events in order of
importance:
1. Team milestone goal (multiple of 5): `{team} reaches {count} goals`
   (importance 4).
2. Lead change: `{player} scores, putting {team} in the lead` (importance 3).
3. tying the game: `{player} scores, tying the game` (importance 2).
4. Other goals: `{player} scores a goal` (importance 1).

## Laserball Game Notability

The game highlight tagline evaluates conditions in order of priority:
1. Focus player had at least one goal: `1 goal` or `{goals} goals`.
2. Focus player had at least one assist: `1 assist` or `{assists} assists`.
3. Focus player had multiple steals (>= 2): `{steals} steals`.
4. Focus player had a hit diff over 1.4: `{hit_diff:.1f} hit diff`.
5. Focus player cleared more than once (>= 2): `{clears} clears`.

In any of these 5 cases, if the player had more than 20 blocks, `, {blocks} blocks`
is appended.

If none apply, the fallback is: `{blocks}/{blocked_by_others} blocks`.

## Laserball Focus Player Ball Indicators

* In Laserball games, the focus player ball indicators (`ball_indicator` and
  `ball_indicator_2`) toggle their visibility between each other.
* Default speed multiplier is 3.0 (3 toggles per second, toggle interval of
  333.33 ms).
* Speed is configurable via `speed` in element configuration (`ball_indicator`
  or `ball_indicator_2`), `style.speed`, or `ball_indicator_speed` / `speed`
  in the top-level HUD configuration.
* Ball indicators fade in and out during each toggle interval using a sinusoidal
  alpha curve (`alpha = sin(pi * progress)` where progress goes from 0.0 to 1.0
  during the toggle interval).

## Laser Tag GoPro LUT Tone Curve Controls

* To handle dark laser tag footage with bright lights (vest LEDs, lasers, bases):
  - `Shadows`: Brightens dark tones with weight $4v(1-v)^2$, peaking in the
    shadows ($v \approx 0.33$) and tapering to zero at pure black ($v=0$) and
    pure white ($v=1$).
  - `Highlights`: Adjusts bright areas with weight $v^2$ to recover detail and
    prevent overexposure.
  - `Gamma`: Midtone power curve $v^{1/\gamma}$ that brightens shadows and
    midtones while mathematically pinning 0.0 at 0.0 and 1.0 at 1.0.
  - `Light Rolloff`: Soft shoulder compression using $\tanh$ above a knee
    threshold ($1 - 0.35 \times \text{rolloff}$) to prevent harsh digital
    clipping of laser tag LEDs and lasers.

## HUD Video Merger FFmpeg Parameters

* `hudmerge` and `HudMergeOptions` support an optional `ffmpeg_parameters`
  parameter (string or list of strings).
* When specified, the additional parameters are parsed and appended to the
  FFmpeg command after default video encoding options and before the
  output file path.
* This allows overriding default encoder settings (e.g. `-c:v libx265`, `-crf`,
  etc.) or specifying additional options (such as `-threads` or bitrate).

## Authoritative Player Lives from TDF (Type 11 Records)

* If a TDF file contains rows where the first column is 11, it provides
  information about the number of lives for a player.
* Row format:
  - Column 1: Record type (11)
  - Column 2: Timestamp in milliseconds from game start
  - Column 3: Player entity ID
  - Column 5: New number of lives
* If there is at least one row with column 11, player lives are not computed
  from game events (zaps, missiles, nukes, medic resupplies, team boosts).
  Instead, the TDF file is used as the authoritative source for the number of
  lives of each player at any time.

## Authoritative Player Ammo from TDF (Type 12 Records)

* If a TDF file contains rows where the first column is 12, it provides
  information about the number of shots (ammo) for a player.
* Row format:
  - Column 1: Record type (12)
  - Column 2: Timestamp in milliseconds from game start
  - Column 3: Player entity ID
  - Column 5: New number of shots (ammo)
* If there is at least one row with column 12, player ammo/shots are not
  computed from game events (zaps, base hits, beacons, ammo resupplies, team
  boosts). Instead, the TDF file is used as the authoritative source for the
  number of shots of each player at any time.


