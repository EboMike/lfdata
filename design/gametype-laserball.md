# Laserball Game Type

The rules for the Laserball game type:

## Player data

* A player has unlimited lives and shots.
* There are no different player roles.
* Downtime is 8 seconds. Normally 4 seconds safe, 4 seconds resettable, but this can be changed.
* There are no special points.
* There are no hitpoints.
* Friendly fire doesn't do anything.

## Game structure

The game is played in rounds. The game will always run its predetermined length with as many rounds
as can fit in this time period.

At the beginning of each round, one player will be randomly assigned as the ball carrier. At any
point during the game, there will be one and only one ball carrier (except in special variants of
Laserball).

A player will attempt to score a goal by tagging the enemy base. This will award the team a point
and end the round.

The general rules of resetting apply.

## Possible activity

Any player can zap an enemy player. This will put the tagged player down for the predetermined
period and is called a "block".

If a player zaps an enemy player who is carrying the ball, the ball is stolen, the zapped player is
down, and the zapping player is now the ball carrier.

If a ball carrier zaps a teammate, the ball is passed to the zapped teammate. The teammate stays
up.

If the ball carrier zaps the base of their own team, the ball is "cleared", which will make another
randomly chosen player the ball carrier.

## Stats and scores

Players have the following stats:

* **Goals**: The number of times the player has tagged an enemy base to score a goal. (10000 points)
* **Assists**: The number of times the player has passed the ball to a teammate who then immediately
  scored a goal. (10000 points)
* **Clears**: The number of times the player has cleared the ball from their own team. (100 points)
* **Steals**: The number of times the player has stolen the ball from an enemy player. (100 points)
* **Blocks**: The number of times the player has zapped ("blocked") an enemy player. (1 point)

Note that the points are used to compute a score for the given player, but this score will not be
shown in any visualization. It is only used to rank the players when showing the current roster.

Note that no number can exceed 99. For example, if the combined number of clears and steals is 100,
this will add up to only 9900 to be added to the total points for the player. This way, stats like
clears and steals do not affect goals or assists.

## Events

The following events can happen in a TDF file:

| Event name              | Event ID | Description                                              | Entity 1           | Entity 2          |
|-------------------------|----------|----------------------------------------------------------|--------------------|-------------------|
| MISSION_START           | 0100     | * Mission Start *                                        | -                  | -                 |
| MISSION_END             | 0101     | * Mission Over *                                         | -                  | -                 |
| PENALTY                 | 0600     | A player receives a penalty from a referee.              | penalized player   | -                 |
| PASS                    | 1100     | Player passes the ball to another player on the team.    | previous carrier   | new ball carrier  |
| GOAL                    | 1101     | The player scores.                                       | goal scorer        | -                 |
| ASSIST                  | 1102     | The player assisted someone else.                        | assisting player   | goal scorer       |
| STEAL                   | 1103     | Player steals a ball from the enemy ball carrier.        | stealing player    | previous carrier  |
| BLOCK                   | 1104     | Player zaps an enemy player.                             | zapping player     | zapped player     |
| ROUND_START             | 1105     | A new round begins.                                      | -                  | -                 |
| ROUND_END               | 1106     | The round is over.                                       | -                  | -                 |
| GETS_BALL               | 1107     | A player receives a ball at the beginning of a round.    | new ball carrier   | -                 |
| CLEAR                   | 1109     | A player clears the ball, a new player receives it.      | clearing player    | new ball carrier  |
| FAIL_CLEAR              | 110A     | A player tried to clear, but no teammate was up.         | clearing player    | -                 |
| RESET_ON_BASE           | 110B     | The player zaps a neutral base.                          | zapping player     | base              |

## Penalties

Penalties are shown as game events. If a player is penalized, they're beginning
a new downtime. They will also incur the penalty specified in the mission data
type. The game keeps track of how many penalties each player has.
