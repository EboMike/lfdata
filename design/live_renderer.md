# LF Live Renderer

The live renderer is the counterpart to the LF Live parser, as
described in @live_parser.md.

## General functionality

The live renderer is a separate binary written in C++. On
startup, it will connect to a LF Live parser as a consumer by
connecting to TCP consumer port.

On startup, the renderer will open one or more windows as
set in its visualization configuration file.

While data is being sent, all windows are being updated with
the current data.

All windows remain open, even while there is no active session.
A new session or a new game will reuse the existing windows.

In addition to the windows, there is another window with control
elements for the binary itself, for example to load a different
visualization configuration file.

The renderer will use a GPU if possible.

NOTE: The lfstats integration will be TBD.

## Render Components

The windows will be populated using various elements that each
use one of these components, which themselves might use more
components:

### Template

A template is a reusable list of elements. It has a fixed size
and contains a list of elements. The list of possible elements
depends on what the template is used for.

### Text

A text element, which might be formatted using the formatting
elements described in the parser definition (for example
`<font color="#00ff00">`). It could also contain image assets.

Strings also support placeholders. These are:

*   **{game_type}**: The current game type (SM5, Laserball)
*   **{center}**: Name of the center (Loveland, Syracuse, etc.)

Text elements by default have a black outline around them.

Parameters:

*   **Color**: Text color
*   **Font size**: The font size. This is a number that will describe
    the size irrespective of the image resolution. A font size of 20
    will take up about 1/40 of the image's height of a window that is
    800 pixels high.
*   **Alignment**: Horizontal alignment relative to container
    dimensions. Left, center, right.

### Image

An image asset, potentially loaded dynamically from a page, or
defined in the editor by pointing to an image on the local
file system.

Images with alpha channels are supported.

*   **Opacity**: A float value from 0.0 (invisible) to 1.0
    (opaque).
*   **Image file**: If set, points to a local file with the
    image data.

### Lists

A list of elements. This could be a list of players, or a list
of scores within a score card.

Note that this is a superclass and not part of an actual UI
layout. A layout would contain a subclass like "Player list"
or "Scorecard element".

Parameters:

*   **Orientation**: Horizontal or vertical
*   **Sort order**: Order of the elements, depends on subclass.
*   **Template**: A template for each element.
*   **Header Template**: An optional template for a header.
*   **Elements**: All, or a specific one by its index.

### Team Scorecard

A team scorecard is a List subclass. Its template is a "scorecard
row".  Its header template is a "scorecard
header row". Each list element is the score for one player. The sort
order is either player ID or player ranking.

Parameters:

*   **Add totals**: Boolean. If enabled, will add a final row, always
    at the end, with the stats of the dummy player for the team.
*   **Team index**: If used as a stand-alone element, the index of the
    team to show the scorecard for.
*   **Scorecard row template**
*   **Scorecard header row template**

### Game Scorecards

A list subclass with the elements being team scorecards. Its
template is a "scorecard row". Its header template is a "scorecard
header row".

*   **Add totals**: Boolean. If enabled, will add a final row, always
    at the end, with the stats of the dummy player for each team.
*   **Sort order**: "Team index" or "Team ranking".
*   **Scorecard row template**
*   **Scorecard header row template**

### Team Roster

A list subclass. Its template is a "player profile". Each list
element is the player on one team.

*   **Sort order**: "Player index" or "Player ranking".
*   **Player profile Template**

### Event scroller

A list of recent event messages. It scrolls up as new events are
being added to the bottom. The scroller is optionally slightly tilted,
like a Star Wars scroller.

Parameters:

*   **Tilt**: The tilt amount of the scroller, defaults to 10 degrees.

In addition, it has all parameters of a text element.

## Render elements

Every render elements has a position and a size. These are given
in relation to the size of the parent (like the size of the window
they're in).

These are the possible render elements on the top level:

### User-defined text

A text component with a user-defined text.

Parameters:

*   **Text**: The actual text

### Game timer

The amount of time left in the game, in MM:SS. Note that this must
be computed and updated by this binary. The reference point is the
length of the game, and the time at which the beginning of the game
was processed and visualized.

### User-defined image

An image component with a user-defined image.

### Team Scorecard

A team scorecard component.

### Game Scorecard

A game scorecard component.

### Team roster

A team roster component.

### Event scroller

An event scroller component.

## Render elements within templates

These elements are only available within certain templates:

### Player name

A text component with the name of the player.

### Player role

A text component with an image asset showing the role of the player.

### Player score

A text component with the player's current score.

### Player lives

A text component with the player's current lives.

### Player ammo

A text component with the player's current ammo.

### Player missiles

A text component with the player's current missiles.

### Player special points

A text component with the player's current special points.

### Player profile picture

An image component with an image of the player, loaded from the lfstats page.

### Team Logo

An image component with a team logo, loaded from the lfstats page.

## Tmeplates

Template define a collection of render elements to be used in lists.

### Scorecard row

Render elements used for within a score card. It may contain
the following elements:

*   Player name
*   Player role
*   Player score
*   Player lives
*   Player ammo
*   Player missiles
*   Player special points
*   Player goals
*   Player assists
*   Player clears
*   Player steals
*   Player zaps

Note that the content of a scorecard row is generally rendered in the
color of the team.

If the given player is out of lives, it is rendered in gray.

If the give player is down ("down" or "resettable"), it is rendered
in a darker tone.

If the given player has rapid fire, the text is rendered with vertical
lines inside the text in a slightly brighter color, moving right.

### Scorecard header row

Render element used for within a score card. It may contain text
and image assets.

Note that the content of a scorecard header row is generally rendered in
the color of the team.

### Player profile

Render elements used for a player profile. It may contain the
following elements:

*   Player name
*   Player role
*   Player score
*   Player lives
*   Player ammo
*   Player missiles
*   Player special points
*   Player profile picture
*   Team logo

## UI configuration file

The UI configuration YAML file has the following parts:

### Templates

A list of template definitions. For each one:

*   Template ID (numerical primary key)
*   Template name (Display name)
*   Template type (scorecard row, player profile, etc.)
*   List of render elements

### Windows

A list of windows to render. For each one:

*   Window ID (numerical primary key)
*   Window title
*   Window position and size in pixels
*   Preferred monitor ID, if available (depends on the host OS,
    and whether physical devices have permanent IDs)
*   List of render elements

## Main configuration file

The global configuration YAML file has these settings:

*   IP address and port to connect as a consumer of live LF data
*   The UI configuration file to use

## Main control window

The main control window has a connection status indicator on top.

Underneath, it has buttons with the following options:

*   **Reconnect**: Reconnect to the lflive data server if the
    connection is lost. If there is an active connection, it will
    reload the connection, which should cause the server to resend
    the current game state.
*   **UI Editor**: Begins the UI editor mode, described below.
*   **Quit**: Terminate the program, with a confirmation dialog.

The main window also has a menu:

*   **File**:
    *   **Open configuration**: Opens a new global configuration
        file. After doing that, will reset the entire program state.
    *   **Settings**: Opens modal dialog with global settings, with
        "Save" and "Cancel" buttons. Will update the configuration file
        on "Save".
*   **Help**:
    *   **About**: A modal dialog with the application name, version,
        and author.

## UI Editor Mode

While in UI editor mode, the main control window will be replaced by the
UI editor control window.

In this mode, only one UI window is shown at a time.

It has the following buttons:

*   **New window**: Creates a new window. Opens a modal dialog to ask
    for the name of the window title.
*   **Next**: Cycles to the next window to be the one visible.
*   **Previous**: Cycles to the previous window to be the one visible.
*   **Add element**: Adds a new render element.
*   **New template**: Creates a new template. Opens a modal dialog to
    ask for the template name, and a dropbox with possible template
    types.
*   **Save & Back**: Saves all changes and goes back to the main view.

There is also a list box with all templates. Clicking on one will hide
all windows and only show that template so it can be edited. While
editing templates, the following buttons are disabled: "New window",
"next", "previous", "new template". "Save & Back" will change to
"Done with template".

## General code requirements

The renderer updates multiple windows with many graphical elements
in realtime, so it must be very efficient. The render threads can
never block on I/O operations.

Any elements that do not change should cache as much of their
intermediate states and objects as possible.
