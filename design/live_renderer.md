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

Some placeholders exist in the context of a template that involves
one player (player profile, player score row):

* **{player_name}**: The name of the player
* **{player_score}**: The score of the player
* **{player_lives}**: The player's number of lives
* **{player_ammo}**: The player's current number of shots left
* **{player_missiles}**: The player's number of missiles
* **{player_special_points}**: The player's number of special points
* **{player_goals}**: The player's number of goals
* **{player_assists}**: The player's number of assists
* **{player_clears}**: The player's number of clears
* **{player_steals}**: The player's number of steals
* **{player_zaps}**: The player's number of zaps
* **{player_medic_hits}**: The player's number of medic hits
* **{player_shots_fired}**: The player's number of shots fired
* **{player_shots_landed}**: The player's number of shots landed
* **{player_accuracy}**: The player's accuracy
* **{player_missiles_fired}**: The player's number of missiles fired
* **{player_missiles_landed}**: The player's number of missiles landed
* **{player_total_games}**: The player's total number of games played
  across all formats, empty string if unknown
* **{player_total_games_this_format}**: The player's total number of
  games played in this format (SM5/Laserball/etc), empty string if unknown
* **{player_total_games_this_format_center}**: The player's total number
  of games played in this format (SM5/Laserball/etc) at this center,
  empty string if unknown

Text elements by default have a black outline around them.

Parameters:

*   **Color**: Text color
*   **Font size**: The font size. This is a number that will describe
    the size irrespective of the image resolution. A font size of 20
    will take up about 1/40 of the image's height of a window that is
    800 pixels high.
*   **Alignment**: Horizontal alignment relative to container
    dimensions. Left, center, right.
*   **Vertical spacing**: Extra spacing between lines. This scales
    proportionally with the window height (relative to an 800-pixel-high
    window), ensuring line spacing scales consistently when a window is
    resized.

### Image

An image asset, potentially loaded dynamically from a page, or
defined in the editor by pointing to an image on the local
file system.

Images with alpha channels are supported.

Parameters:

*   **Opacity**: A float value from 0.0 (invisible) to 1.0
    (opaque).
*   **Image file**: If set, points to a local file with the
    image data.
*   **Fit**: How the image should be sized and positioned within
    the boundaries of the element.
    *    **Scale**: Scale to fit within boundaries, keeping aspect ratio.
    *    **Crop**: Scale to fill boundaries, keeping aspect ratio.
    *    **Stretch**: Stretch to fill boundaries, ignoring aspect ratio.
*   **Tint team color**: Can be used only if the image is in the context of
    a team (for example a team score card). Float value. If >0.0, the image
    will be tinted with the team color (higher value = higher tint). 

### Video

A video clip element that will be played repeatedly. Audio is
ignored.

Parameters:

*   **Opacity**: A float value from 0.0 (invisible) to 1.0
    (opaque).
*   **Video file**: If set, points to a local file with the
    video data.
*   **Fit**: How the video should be sized and positioned within
    the boundaries of the element.
    *    **Scale**: Scale to fit within boundaries, keeping aspect ratio.
    *    **Crop**: Scale to fill boundaries, keeping aspect ratio.
    *    **Stretch**: Stretch to fill boundaries, ignoring aspect ratio.
*   **Playback speed**: Multiplier for the playback speed, defaults to 1.0.
*   **Tint team color**: Can be used only if the video is in the context of
    a team (for example a team score card). Float value. If >0.0, the video
    will be tinted with the team color (higher value = higher tint). 

### Background

This is not a component by itself, but it can be used by other components,
such as lists. It will be rendered immediately underneath the element it is
assigned to.

Parameters:

*   **Color**: If set, a simple RGB color.
*   **Image**: If set, an image. Has all the parameters of "Image" components.
*   **Video**: If set, a video. Has all the parmaters of "Video" components.
*   **Opacity**: A float value from 0.0 (invisible) to 1.0
    (opaque).
*   **Corner radius**: The corner radius of the background. Defaults to 0.0.

### Padding and Margin

Every element has padding and margin. Each one of these has a value for left,
right, up, down:

*   **Padding**: Insets around the element's content. Expands the extents of
    the element when rendered. The element's background covers the padding area.
*   **Margin**: Insets outside the padding area. Expands the extents of the
    element when rendered. The element's background is not rendered in the
    margin area.

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
*   **Background**: The background for this element.

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
header row". Because a game scorecard is a nested list, it has two
background settings: one for the game scorecard as a whole (behind
all teams), and one for each individual team scorecard.

*   **Add totals**: Boolean. If enabled, will add a final row, always
    at the end, with the stats of the dummy player for each team.
*   **Sort order**: "Team index" or "Team ranking".
*   **Scorecard row template**
*   **Scorecard header row template**
*   **Background**: Background for the overall game scorecard.
*   **Team background**: Background for each team scorecard within it.

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

### Messages display

A fixed number of text fields, one underneath each other, that can
display messages, for example important game messages.

When a message is issued, it will be shown in the first line from the
top that is not currently showing a line. Once a message is shown, it
will be displayed for a fixed amount of the and then fade out.

Messages have numerical IDs. If a message with the same ID is issued
again, it will replace the existing message, if it is still displayed,
and its fade-out timer reset.

Parameters:

*   **Number of lines**: Number of lines to allocate for showing messages
*   **Display time**: The number of seconds a message is shown before it
    fades out. Defaults to 4.0.
*   **Fadeout time**: The number of seconds it takes for a message to fade
    out. Defaults to 1.0.

## Render elements

Every render elements has a position and a size. These are given
in relation to the size of the parent (like the size of the window
they're in).

Every element also has a Z position, an integer. Elements with higher
Z order render on top of elements with a lower one.

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

## Important game messages

A "messages display" component that shows all important game messages.

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
*   Player medic hits
*   Player shots fired
*   Player shots landed
*   Player accuracy
*   Nukes activated
*   Nukes detonated
*   Player accuracy string (shown as "shots landed/shots fired (accuracy)", for
    example "30/60 (50%)". Empty string if no shots fired.)
*   Missiles fired
*   Missiles landed
*   Missile accuracy string (shown as "missiles landed/missiles landed", for
    example "3/5". Empty string if player role has no missiles, otherwise
    always shown, even "0/0").

Note that the content of a scorecard row is generally rendered in the
color of the team.

If the given player is out of lives, it is rendered in gray.

If the give player is down ("down" or "resettable"), it is rendered
in a darker tone.

If the given player has rapid fire, the text is rendered with a repeated
gradient moving right that brightens the text itself (without affecting
surrounding pixels).

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
*   Player medic hits
*   Player shots fired
*   Player shots landed
*   Player accuracy
*   Nukes activated
*   Nukes detonated
*   Player accuracy string (shown as "shots landed/shots fired (accuracy)", for
    example "30/60 (50%)". Empty string if no shots fired.)
*   Missiles fired
*   Missiles landed
*   Missile accuracy string (shown as "missiles landed/missiles landed", for
    example "3/5". Empty string if player role has no missiles, otherwise
    always shown, even "0/0").

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
*   Default profile picture fallback URL to use if a player has no picture

## Command line options

*   **--config**: Path to global configuration YAML file.
*   **--preferences**: Path to local preferences YAML file.
*   **--default-profile-picture-url**: Default fallback URL for player profile
    pictures. Can also be set via `DEFAULT_PROFILE_PICTURE_URL` in a local `.env`
    file.
*   **--lfstats-api-key**: API key to authenticate requests against LFstats. Can
    also be configured via the `LFSTATS_API_KEY` setting in a local `.env` file.
*   **--lfstats-test-mode** (or **--lfstats-test**): Run in LFstats test
    mode, using local fixture data instead of live network services.
*   **--lfstats-test-data-dir**: Directory path containing LFstats test
    fixtures.
*   **--max-frames**: Maximum number of frames to render before exiting.

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

The main control window, and its dialogs, can show data that is
dynamically loaded. While data is being populated for a control element,
the element should be disabled, and if it has text, it should display
"Loading...". If data could not be loaded (for example, the server is
unreachable), the element should remain disabled and say "ERROR".

Selecting a competition from the dropdown automatically loads the competition
details and updates player metadata (such as profile picture URLs matched by
player entity ID) in the live state store. If a player does not have a picture
URL in the competition data, the configured default profile picture URL is
used.

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
*   **Save & Exit**: Saves all changes and goes back to the main view.
    Closing the UI editor window is equivalent to clicking "Save & Exit".

There is also a list box with all templates. Clicking on one will hide
all windows and only show that template so it can be edited. While
editing templates, the following buttons are disabled: "New window",
"next", "previous", "new template". "Save & Exit" will change to
"Done with template".

There is also a list box with all elements in the current window. Selecting
them highlights them in the window, and shows all their properties
and allows them to be edited.

## General code requirements

The renderer updates multiple windows with many graphical elements
in realtime, so it must be very efficient. The render threads can
never block on I/O operations.

Any elements that do not change should cache as much of their
intermediate states and objects as possible.

* Every update to the live renderer must increase the version number in
  src/live_renderer/version.hpp to verify that a new executable was built.
