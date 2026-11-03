# LF Live Parser

The live parser receives TDF data in real-time and translates them into
game states that can be used to render a visualization.

## Main operation

`lflive` is a separate binary that receives TDF files through a TCP
connection. Consumers can connect to this binary with a TCP connection
to receive events as they come in.

All its content is in the `lflive` subdirectory. 

### The TDF listener

On startup, the binary opens a TCP port that waits for a connection at
a preconfigured port.

When a connection is established, the sender will send the contents of
a TDF file as a game is in progress. This might be in UTF-16LE or in
UTF-8 encoded with BOM markers.

When a session begins, the process sets up the game state. It will
listen to incoming events from the TDF file to understand the game state:
The type of game being played (SM5, Laserball, etc), the teams that
are playing, and the players in each team, and will set up the game
state accordingly.

As data from the TDF file is being sent, the data is being processed and
the game state updated. Whenever the game state changes, the process will
send updates to all listeners.

Once the TDF indicates that a game is over, or if the connection is
terminated, the game is considered over, although the session data will
remain in memory and accesible until a new session is started.

The listener might call the lfstats API to retrieve some information not
present in the TDF.

### Broadcasting events

After all data to establish the game data have been established (game
format, teams, player rosters), and whenever any game state changes,
the server will send updates to all listeners that have connected to the
server.

### Consumer connections

The binary allows for any number of consumers to connect. If there is
an active session at the time of the connection, the binary will send
all events that are necessary to determine the current game state (i.e.
game format, teams, rosters, current stats for every player, followed by
a PRESYNC_END event). Keep in mind that "current" is everything that would
have been sent up to this point to consumers, i.e. everything up to the
preroll time.

After that point, the binary will continue to send events for this
session and all upcoming sessions until a connection is severed.

## Preroll delay

In the configuration, it is possible to set up a delay. This means that
the TDF file will set the game state and send it with a predetermined
delay.

Example: The delay is set to 500ms. A game is started at 10:47:20 and
0 milliseconds. At 10:47:30, the server will broadcast the game state
as it is at 10:47:29 and 500 milliseconds.

## Internal game state

The game state is stored in memory, and will be persisted in a sqlite
database every second. A new session will delete the previous persisted
game state.

### Game objects

The server maintains a list of objects that persist throughout the
session. Each object is assigned a numerical primary key that is
used to reference to it in the data sent to the listener.

All data points that change throughout the game are stored in tables
with a timestamp so that it's possible to see the game state up to a
certain point.

#### Teams

A team has the following information:

*   Team primary key (numerical ID)
*   Team name
*   Team color
*   Team RGB
*   Total team score (sum of all points in SM5, sum of all goals in Laserball)

#### Players

A player has the following information:

*   Player primary key (numerical ID)
*   Entity ID (ID of a player as referenced in the TDF data, like `#1A2b3c`)
*   Player name
*   Team ID
*   Role (if supported by game format)
*   Number of lives (if supported by game format)
*   Number of shots (if supported by game format)
*   Number of missiles (if supported by game format)
*   Number of special points (if supported by game format)
*   Number of hitpoints (if supported by game format)
*   Score
*   Number of goals (if supported by game format)
*   Number of assists (if supported by game format)
*   Number of blocks (if supported by game format)
*   Number of clears (if supported by game format)
*   Number of steals (if supported by game format)
*   Current player state. Can be one of the following:
    *   **Up** (0): Player is active.
    *   **Down** (3): Player is down and cannot be zapped.
    *   **Resettable** (2): Player is resettable, i.e. down but can be zapped (reset).
    *   **Dead** (4): The player is no longer in the game.
*   Whether the player currently has rapid fire

#### Targets (bases, etc)

A target (like a base) is defined like this:

*   Target primary key (numerical ID)
*   Target entity ID as used in the TDF file
*   Target name
*   Target color (RGB value, like `#ff00ff`)

## The format of the data sent to consumers 

Data sent to consumers is UTF-8 encoded text. Every separate data point sent
is terminated by a newline.

Every line is tab-delimited. The first value is always the type of
data being sent. The second value is always the time of the event
in milliseconds starting from the beginning of the game.
The remaining data depends on the data type.

Event messages are text that contain formatting. There is support for
very specific HTML-like tags. Specifically:

*   `<font color="#ff0000">Text</font>` - The text within the `<font>`
    will be displayed in the specified color.

### Event messages

Any event message (for example `PlayerA zaps PlayerB` will always format
the player names so they are in the color of their team, for example
`<font color="#ff0000">PlayerA</font> zaps <font color="#0000ff">PlayerB</font>`).

### List of data types

| Data Type identifier | Description | Value 1 | Value 2 | Value 3 | Value 4 | Value 5 |
| -------------------- | ----------- | ------- | ------- | ------- | ------- | ------- |
| 1 | Current score for a team | Team primary key | New team score |   |   |   |
| 2 | Time when the game started | Timestamp YYYYMMDDHHMMSSmmm |   |   |   |   |
| 3 | Current score for a player | Player primary key | New score |   |   |   |
| 4 | Current lives for a player | Player primary key | New number of lives |   |   |   |
| 5 | Current shots for a player | Player primary key | New number of shots |   |   |   |
| 6 | Current special points for a player | Player primary key | New number of special points |   |   |   |
| 7 | Current hitpoints for a player | Player primary key | New number of hitpoints |   |   |   |
| 8 | Event for the event scroller | Formatted event message |   |   |   |   |
| 9 | Current player state | Player primary key ID | Numerical player state value |   |   |   |
| 10 | Current missiles for a player | Player primary key | New number of missiles |   |   |   |
| 11 | Current goals for a player | Player primary key | New number of goals |   |   |   |
| 12 | Current assists for a player | Player primary key | New number of assists |   |   |   |
| 13 | Current blocks for a player | Player primary key | New number of blocks |   |   |   |
| 14 | Current steals for a player | Player primary key | New number of steals |   |   |   |
| 15 | Description of a team | Team primary key | Team name | Team RGB value (example: `#ff0000`) |   |   |
| 16 | Description of a player | Player primary key | Player name | Player entity ID | Team primary key | Role (if supported, e.g. `commander`) |
| 17 | Type of game | Game type ("SM5", "Laserball") | Maximum length of the game in seconds |   |   |   |
| 18 | Current ball carrier | Player primary key |   |   |   |   |
| 19 | Round end (used in Laserball) |   |   |   |   |   |
| 20 | Round begins (used in Laserball) |   |   |   |   |   |
| 21 | Player captured a base | Player primary key | Base primary key |   |   |   |
| 22 | Description of a base | Base primary key | Base name | Base RGB |   |   |
| 23 | New rapid fire state for a player | Player primary key | 1 = has rapid fire, 0 = doesn't have rapid fire |   |   |   |
| 24 | `PRESYNC_END` - indicates concluding data for newly joined consumer |   |   |   |   |   |
| 25 | Important game event (e.g. `Commander {name} has a nuke`) | Formatted event message |   |   |   |   |
| 26 | New player ranking (typically all players in order of score within their team, highest first)  | Team primary key | Commma-separated list of player primary keys |   |   |   |
| 27 | New team ranking (typically all teams in order of score, highest first)  | Commma-separated list of team primary keys |   |   |   |   |
| 98 | New game start - indicates previous session data should be erased |   |   |   |   |   |
| 99 | The game is over - concludes stream for this game |   |   |   |   |   |

Note that not every TDF file event has a matching data type, because some TDF events can be expressed with multiple
data points. For example, a base hit will have multiple events, like possibly these:

*   An event of type 5 every time the player shoots at the base to express the new shot count
*   An event of type 8 to say "Player zaps base" or "Player destroys base"
*   An event of type 3 to express that the player's score increased by 1001
*   An event of type 21 that the player has captured the base
*   An event of type 6 for the additional 5 special points, if applicable

Another example: A player drops a nuke.

*   An event of type 8 to say "Player activates nuke"
*   An event of type 25 for the important game event, "player activates nuke"
*   An event of type 6 for the 20 special points taken away
*   An event of type 8 to say "Player detonates nuke"
*   An event of type 25, "Player detonates nuke"
*   An event of type 3 to add 500 points for the player
*   An event of type 4 for every player on the other team still alive to take away up to 3 lives
*   An event of type 9 for every player on the other team still alive to mark them as down, or
    as dead

Likewise, if the nuke doesn't detonate, the events would be explained similar like this:

*   An event of type 25, "PlayerA's nuke canceled by PlayerB"
*   Events to update lives, scores, shots, state of all players involved


## Configuration file

The binary can be configured with a YAML file. Configuration options:

*    The port to listen to for incoming TDF data.
*    The port to listen to for consumers to connect to.
*    The URL of the lfstats API (defaults to https://lfstats.com/api/)

## Command line options

The binary supports the following command line options:

*   `--log_tdf`: If true, every line of TDF file data that is received will be printed to stdout. Default false.
*   `--log_output`: If true, every line of data that would be sent to consumers will be printed to stdout,
    whether or not there are any active consumers. Default false.

## Core code design principles

Because the code maintains multiple TCP connections, there may not be any blocking I/O code. Everything must be async.
Threads should be created as appropriate (with proper data synchronization guards in place).