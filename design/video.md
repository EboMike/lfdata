# Video generation

Video generation will take one game replay and create a video from its game state.

The generator will create individual frames for the game which can be saved as image
files and optionally encoded into a video file.

Unless specified otherwise, the generator will create 60 frames per second, starting
with the beginning of the game, until the game is over, plus an 10 seconds after that.
These numbers are configurable.

A video can be shown with information specific to one player. In this case, there will
be various UI elements that pertain to this one player.

Since this can be a lengthy process, the code should be multithreaded where possible.

The process is done in multiple steps:

## Visual element generator

For each frame, the element generator creates a list of UI elements to be rendered.
A UI element includes:

* Element type (text, etc.)
* Element text (if text)
* Element style (font, color, etc.)

Some elements only show up during certain moments and might fade out. Some elements
might animate over time. The alpha value must be provided for each element.

## Image generator

For each frame, the image generator will take the list of UI elements and create an
image for each frame.

By default, each image has a transparent background, but a solid background color is
configurable.

Each image is saved as a PNG file in the target directory. PNG will have a suffix with
the frame number, always padded with 5 digits.

For example, the very first frame at the beginning of the game has suffix `00000`.
The frame for 100 seconds in for a video with 30 frames per second has suffix `03000`
(100 seconds times 30 frames). The frame for 123434 milliseconds into the game
has suffix `03703`.

## Video file generator

If configured, the video configurator will use `ffmpeg` to encode all PNG files into
a video.

## Configuration

The video generation process can be configured with an optional configuration file.
This file is a YAML file.

### General definitions

#### Styling

Several parts of the configuration involve text styling. A text styling is: Font,
style (normal, italics, bold), size, color, background color. Colors are RGBA.

Also, elements can be generally enabled and disabled.

By default, those are:

* Font: `GoogleSans-Bold`
* Style: normal
* Size: 20
* Color: #ffffffff
* Background color: #00000000
* Fade out time: 2 seconds

The font size is a number that will describe the size irrespective of the image
resolution. A font size of 20 will take up about 1/40 of the image's height.

All text should have a black outline.

#### Positioning

UI elements describe their position through their anchor point in X and Y values
relative to the image. 0.0 is the left-most or top-most point, 1.0 is the right-most
or bottom-most point.

The position includes alignment (left, center, right). The anchor point is typically
the top of the element, and depending on the alignment, the left, center, or right of
the element.

### Main Options

* Video FPS
* Number of milliseconds of footage to add after the game is over
* Main player: The player for whom specific data should be shown
* Image resolution
* Animation function (`linear`, `ease-in-out`, ...). Default is `ease-in-out`.

### UI Element Types

* **Text**: A text, typically on one line.
* **Multi-line text**: Similar to `Text`. By default, up to 3 lines long. Each line
  is independent and does not break into multiple lines. When a new text is added,
  it goes into the first empty line from the top. Each lines has its independent
  timer and fades out after the timer expires.
  Example:
    * A text is set, "text 1", duration 5 seconds. It shows up on the top line.
    * 3 seconds in: A new text is set, "text 2", duration 8 seconds. It shows up in
      the second line because the first is still full.
    * 6 seconds in: A new text is set, "text 3", duration 1 second. It shows up on
      the top line because it is available again.
    * 8 seconds in: A new text is set, "text 4", duration 1 second. It shows up on
      the top line because it is available.
* **Downtime bar**: A horizontal bar indicating that the current player is down.
  This is a combination of the images `assets/downtime-full.png` and
  `assets/downtime-empty.png`. Immediately after the player is down, only
  `downtime-full.png` is visible. As time progresses, more of `downtime-empty.png`
  is visible, starting from the left. So as 30% of the downtime has progressed,
  the left 30% of the image is `downtime-empty.png`, the remainder is
  `downtime-full.png`.
* **Counter**: An indicator for a number, with a max counter. This element has
  several components:
    * A circle that is a complete circle the number equals max, and that is invisible
      if the number is 0. The arc begins in the bottom left quadrant. The arc indicating
      less than 20% is red. The arc indicting less than 50% is yellow. The remainder
      is green.
    * An icon in its center.
    * A string to its right indicating the current and the max with a slash, like
      `15/20`. The color uses the same schema as the circle.
    * Optionally, counters can have visual indicators at regular intervals to indicate
      specific values. For example, an indicator "every 20" would add a gap in the arc at
      the 20, 40, 60 marks up to the end.
* **Scoreboard**: Tables with scores of each team, details below.
* **Event scroller**: A list of events that happened up to this point. Whenever an
  event of any type happens, it will be added to the bottom and the scroller will
  smoothly scroll up. The scroller is slightly tilted, like a Star Wars scroller, with
  a configurable tilt (defaults to 10 degrees). The name of a player will be shown in
  their team's color. Do NOT include "miss" events (like `(Player) misses`).

### UI Element options

All elements are enabled by default but can be disabled in the configuration.

The default position is in X, Y.
If specified, the extents are the length and width as X, Y using the same units.

"Icon" is a PNG file in the `assets` directory.

| Element                                                                             | Element Type    | Default Position | Extents    | Anchor | Icon     | Font size |
|-------------------------------------------------------------------------------------|-----------------|------------------|------------|--------|----------|-----------|
| Game type                                                                           | Text            | 0.98, 0.96       |            | right  |          | 12        |
| Time: how far into the game, as `MM:SS` (nothing else). Stops when the game is over | Text            | 0.98, 0.22       |            | right  |          | 40        |
| Player name                                                                         | Text            | 0.5, 0.05        |            | center |          | 24        |
| Player role (Just the role name, nothing else)                                      | Text            | 0.5, 0.09        |            | center |          | 16        |
| Player's number of lives                                                            | Counter         | 0.25, 0.92       | 0.05, 0.05 | left   | lives    | 18        |
| Player's number of shots, if applicable                                             | Counter         | 0.35, 0.92       | 0.05, 0.05 | left   | shots    | 18        | 
| Player's number of missiles, if applicable                                          | Counter         | 0.45, 0.92       | 0.05, 0.05 | left   | missiles | 18        |
| Player's number of hitpoints, if applicable                                         | Counter         | 0.55, 0.92       | 0.05, 0.05 | left   | shields  | 18        |
| Player's number of special points, if applicable. Special rule: always green        | Counter         | 0.65, 0.92       |            | left   | sp       | 18        |
| Player's score                                                                      | Text            | 0.98, 0.05       |            | right  |          | 36        |
| Scoreboard                                                                          | Scoreboard      | 0.02, 0.3        | 0.4, 0.4   | left   |          | 15        | 
| Downtime                                                                            | Downtime bar    | 0.3, 0.14        | 0.4, 0.03  | left   |          | 18        |
| Player events: Events relevant to the current player                                | Multi-line text | 0.5, 0.18        |            | center |          | 18        |
| Important game events: Events that affect the entire game, for example nukes        | Multi-line text | 0.5, 0.28        |            | center |          | 20        |
| All game events                                                                     | Event Scroller  | 0.75, 0.6        | 0.25, 0.25 | left   |          | 16        |
| Date of the game                                                                    | Text            | 0.98, 0.92       |            | right  |          | 18        |
| User defined text 1 (disabled by default)                                           | Text            | 0.1, 0.6         |            | left   |          | 20        |
| User defined text 2 (disabled by default)                                           | Text            | 0.1, 0.7         |            | left   |          | 20        |

Special considerations:

* **Time**: Use the font `advanced_pixel_lcd-7` by default.
* **Missiles** and **hit points**: Visual indicators at every point.
* **Special points**: Visual indicators at the interval depending on the role:
  * **Commander**: Every 20.
  * **Scout** and **Ammo**: Every 15.
  * **Medic**: Every 10.
  * **Heavy**: None.
* **Date of the game**: The date is extracted from the game TDF file. This
  field takes an optional additional parameter, `format`, that specifies
  how to format the date using a Python date formatting string.

## Scoreboard

The scoreboard shows as a table for each team underneath each other. The scoreboards
are ordered by which team has a higher combined score. If the order changes, the
scoreboards animate to change their ordering.

The header text is white and by default uses the font `D Day Stencil`.

The scoreboard will show (columns omitted if the game type does not
have them):

* Player
* Player role
* Player score
* Player lives
* Player shots
* Player missiles
* Player special points

As a last row, there is a sum of each value each column.

The tables will have a semi-transparent, semi-saturated background in the color of the
team. The player rows will use the fully saturated color of the team. If a player
is down, the row's text show in a dimmed color. If a player has no lives, the
row's text will be in gray.

The scoreboard does not have any lines or background color by default, but they
can be enabled separately.

For roles, do not write the text. Instead, use the PNG file in `assets/sm5`
with the role name in lower case.

## SM5 rules

### Player events

In SM5, the following player events might be shown. Each event shows up for 3 seconds
by default:

| Message to display                              | Trigger event                                                |
|-------------------------------------------------|--------------------------------------------------------------|
| Zapped <player name>                            | Zapped an enemy                                              |
| Zapped by <player name>                         | Zapped by an enemy                                           |
| FRIENDLY zap <player name>                      | Zapped a teammate                                            |
| FRIENDLY zap by <player name>                   | Zapped by a teammate                                         |
| Missiled <player name>                          | Missiled an enemy                                            |
| Missiled by <player name>                       | Missiled by an enemy                                         |
| FRIENDLY missile <player name>                  | Missiled a teammate                                          |
| FRIENDLY missile by <player name>               | Missiled by a teammate                                       |
| Resupplied shots by <ammo name>                 | An ammo resupplied this player                               |
| Resupplied lives by <medic name>                | A medic resupplied this player                               |
| Double-resupply by <ammo name> and <medic name> | Both ammo and medic resupplied this player within a second   |
| Shot-boosted by <ammo name>                     | An ammo used their ammo boost and this player received shots |
| Life-boosted by <medic name>                    | A medic used their life boost and this player received lives |

### Important game events

The following global events will be shown:

| Message to display                         | Trigger event                                                                                                  |
|--------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| <player name> activates nuke               | A commander is activating a nuke                                                                               |
| <player name> detonates nuke               | A nuke has been activated                                                                                      |
| <player name> nuke canceled                | A commander is down after activating and before detonating a nuke (see SM5 rules for the exact message to use) |
| <player name> eliminated                   | A player ran out of lives                                                                                      |
| <team name> <medic name> has <lives> lives | If a medic on either team lose a life, and their current number of lives is greater than 0 and divisible by 5  |

By default, global events will be shown for 5 seconds.
The "activates nuke" event is shown until the nuke detonates or is canceled.
