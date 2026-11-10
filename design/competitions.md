# Competitions

There is the concept of competitions. A competition is an event that occurs
typically at one site in a given timeframe.

## Key elements of a competition

### Teams

The competition has a list of teams. Each team has:

- Team slug ID, the primary key to reference it.
- Name
- Short name (typically just 3 or 4 characters)
- A list of players
- A logo (a URL to an image asset).

### Schedule

The competition has a schedule of games to be played, this is a list of
scheduled games.

### Scheduled game

A schedule game has the following data points at all times:

- Names of each team playing. NOTE that this might not always map to a team in
  the "Teams" list. Some competition have games where each side comprises
  multiple teams.
- Logos for each team playing
- Scheduled start timestamp
- Scheduled end timestamp
- Game name. This is often "R{round_number} M{match_number} G{game_number}", for
  example `R1 M3 G2`. In some formats, like Laserball, there is often `H`
  instead of `G` to indicate which half of the game it is, like `R2 M3 H1`. If
  there is an overtime game as a tiebreaker, it could be `R2 M3 OT1`.
- A round number (optional)
- A match number (optional)
- A game number (optional, always an integer)

After a game is complete, the following data points are also available:

- Score for each team
- Score differential between the two teams
