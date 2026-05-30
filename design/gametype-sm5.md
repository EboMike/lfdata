# SM5 Game Type

The rules for the SM5 game type:

## Player data

* A player starts with a certain number of lives
* A player starts with a certain number of shots
* Downtime is 8 seconds. 4 seconds safe, 4 seconds resettable
* A player starts with 0 special points. Maximum is 99.
* Some players have missiles
* Players have a shot strength. That is how many hitpoints a zap
  takes away.
* Players have hitpoints. They will only go down if they lose
  all hitpoints, and will regain their hitpoints after the downtime
  is over.
* Scouts can have rapid fire. They start with no rapid fire.

## Player roles

A player will have one of 5 roles:

* **Scout**: Scouts can use 15 special points to enable rapid fire.
* **Medic**: A medic can zap friendly players to replenish their
  lives.
* **Ammo**: An ammo can zap friendly players to replenish their
  shots. The ammo has unlimited shots.
* **Heavy**: No special features.
* **Commander**: Starts with 5 missiles. Can use 20 special points
  to activate a nuke. After a few seconds, the nuke with detonate
  and take 3 lives from every player in the other team, no matter
  what state they are in.

## Player data

| Role      | Lives on start | Shots on start | Missiles on start | Lives gained when zapped by medic | Shots gained when zapped by ammo | Max number of lives | Max number of shots | Hitpoints | Shot strength |
|-----------|----------------|----------------|-------------------|-----------------------------------|----------------------------------|---------------------|---------------------|-----------|---------------|
| Scout     | 15             | 30             | 0                 | 3                                 | 10                               | 30                  | 60                  | 1         | 1             |
| Medic     | 20             | 15             | 0                 | 0                                 | 5                                | 20                  | 20                  | 1         | 1             |
| Ammo      | 10             | 0              | 0                 | 3                                 | 0                                | 20                  | 0                   | 1         | 1             |
| Heavy     | 10             | 20             | 5                 | 3                                 | 5                                | 20                  | 40                  | 3         | 3             |
| Commander | 15             | 30             | 5                 | 4                                 | 5                                | 30                  | 60                  | 3         | 2             |

## Bases

Every player capture each base except their own once during the game.
It is captured by tagging it three times or by missiling it. They
get 1001 points and 5 special points.

If an entire team is eliminated, all members of the other team will
be awarded all bases. They will automatically receive the points and
special points for bases they had not captured yet.

## Lives

If a player has no lives left, they are eliminated and out of the
game. No further events will apply to them.

## Missiles

Locking missiles does not affect any game state. Firing a missile,
even a miss, against any target, will deduct one missile.

## Shots

Every attempt to zap a target will deduct one shot.

## Resupply

If a medic or an ammo tags a player on their own team, they will give them
lives or shots respectively. When this happens, the resupplied player will be down.
A scout will lose rapid fire if they had it.

Medic and ammos have "boosts". A medic can use 15 special points to use a boost. An
ammo can use 10 special points to a use a boost. This will resupply their team.
Scouts will not lose rapid fire if they are boosted.

They will only resupply players where all these conditions are met:

* Players who are on their team
* Players who are currently not down
* Players who still have lives left
* Not themselves

## Score

Players can get or lose score points and special points through the following
actions:

| Event                   | Score | Special points | Lives lost |
|-------------------------|-------|----------------|------------|
| Zap enemy player        | 100   | 1              | 0          |
| Zap own team member     | -100  | 0              | 0          |
| Missile enemy player    | 500   | 2              | 0          |
| Missile own team member | -500  | 0              | 0          |
| Capture base            | 1001  | 5              | 0          |
| Detonate nuke           | 500   | 0              | 0          |
| Get zapped              | -20   | 0              | 1          |
| Get missiled            | -100  | 0              | 2          |
| Get nuked               | 0     | 0              | 3          |

Note: Scouts do not get special points while they have rapid fire.

Special points can never exceed 99.

## Premature ending

The game ends if all members of the enemy team have been eliminiated.

## Events

The following events can happen in a TDF file:

| Event name              | Event ID | Description                                              | Entity 1           | Entity 2          |
|-------------------------|----------|----------------------------------------------------------|--------------------|-------------------|
| MISSION_START           | 0100     | * Mission Start *                                        | -                  | -                 |
| MISSION_END             | 0101     | * Mission End *                                          | -                  | -                 |
| SHOT_EMPTY              | 0200     | unused?                                                  | -                  | -                 |
| MISS                    | 0201     | player zaps and misses                                   | zapping player     | -                 |
| MISS_BASE               | 0202     | player zaps base and misses                              | zapping player     | base              |
| HIT_BASE                | 0203     | player zaps base                                         | zapping player     | base              |
| DESTROY_BASE            | 0204     | player zaps and captures base                            | zapping base       | base              |
| DAMAGED_OPPONENT        | 0205     | player zaps enemy, enemy is not down                     | zapping player     | zapped player     |
| DOWNED_OPPONENT         | 0206     | player zaps enemy, enemy is down                         | zapping player     | zapped player     |
| DAMANGED_TEAM           | 0207     | player zaps own team member, member is not down          | zapping player     | zapped player     |
| DOWNED_TEAM             | 0208     | player zaps own team member, member is down              | zapping player     | zapped player     |
| LOCKING                 | 0300     | player locks on a target with a missile                  | locking player     | target            |
| MISSILE_BASE_MISS       | 0301     | player locks missile at base and missed                  | missiling player   | target            |
| MISSILE_BASE_DAMAGE     | 0302     | player fires missile at base, base not destroyed         | missiling player   | target            |
| MISISLE_BASE_DESTROY    | 0303     | player fires missile at base, base captured              | missiling player   | target            |
| MISSILE_MISS            | 0304     | player fires missile and misses                          | missiling player   | -                 |
| MISSILE_DAMAGE_OPPONENT | 0305     | unused?                                                  | -                  | -                 |
| MISSILE_DOWN_OPPONENT   | 0306     | player fires missile at enemy, enemy is down             | missiling player   | downed player     |
| MISSILE_DAMAGE_TEAM     | 0307     | unused?                                                  | -                  | -                 |
| MISSILE_DOWN_TEAM       | 0308     | player fires missile at own team mate, team mate is down | missiling player   | downed player     |
| ACTIVATE_RAPID_FIRE     | 0400     | player activates rapid fire                              | player             | -                 |
| DEACTIVATE_RAPID_FIRE   | 0401     | unused?                                                  | -                  | -                 |
| ACTIVATE_NUKE           | 0404     | player activates a nuke                                  | nuking player      | -                 |
| DETONATE_NUKE           | 0405     | player detonates nuke                                    | nuking player      | -                 |
| RESUPPLY_AMMO           | 0500     | player resupplies ammo                                   | resupplying player | resupplied player |
| RESUPPLY_LIVES          | 0502     | player resupplies lives                                  | resupplying player | resupplied player |
| AMMO_BOOST              | 0510     | player resupplies ammo to entire team                    | resupplying player | -                 |
| LIFE_BOOST              | 0512     | player resupplies lives to entire team                   | resupplying player | -                 |
| PENALTY                 | 0600     | is penalized                                             | entity 1           | -                 |
| ACHIEVEMENT             | 0900     | player completes an achievement                          | player             | -                 |
| REWARD                  | 0902     | player earns a reward                                    | entity 1           | -                 |
| BASE_AWARDED            | 0B03     | player is awarded a base                                 | player             | base              |

## Inferred events

In addition to the events from the TDF file, the replay system will create additional events by analyzing the sequence
of events.

### Nuke cancel

If a commander activates a nuke, but the nuke does not activate within ten seconds, this is a "nuke cancel" event.

The nuke cancel event should have a reason. To find the reason, all events after the `activate nuke` event must be
checked until one of these events is found:

* **Player is downed**: If there is a `DOWNED_TEAM` or `DOWNED_OPPONENT` or `MISSILE_DOWN_TEAM` or
  `MISSILE_DOWN_OPPONENT` event with the nuking player as target:
    * If the acting player is an enemy, this is just a "nuke cancel".
    * If the acting player is a teammate, this is a "nuke cancel by friendly fire".
* **Cancel by resup**: If there is a `RESUPPLY_AMMO` or `RESUPPLY_LIVES` event with the nuking player as the
  target, this is a "nuke cancel by own resup" event.
* **Cancel by enemy nuke**: If there is a `DETONATE_NUKE` nuke by another player, this is a
  "nuke cancel by enemy nuke" event.
* **Game end**: If the game ended before the detonation, this is a "nuke activated too late" event.
