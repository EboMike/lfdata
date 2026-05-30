# Replay system

There is a replay system to regenerate the game state from all data.

## Game state

The game state includes:

* Every player and all their data points at the current time (score,
  lives, ammo, special points, whether they are down, etc.)
* The state for each team (ranking, score, etc.)

The game's timeline starts at 0 milliseconds (the beginning of the game), and
goes for the duration of the game.

The replay system will initialize each player to their startup state
as the game type defines it, then it will go through each event one
by one.

For each event, it will add a record of the following:

* Any changes to any game state data point
* A string describing the event

IMPORTANT: Many game modes include a `Neutral` team. If a team has no players,
do not include it in the replay.

## Game state snapshot

A snapshot is the game state at any given point in the timeline. For example,
a snapshot at 1000ms would include every data point for every player and team
at that given time.


