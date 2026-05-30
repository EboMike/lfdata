# Code generation rules

## Python guidelines

* All code MUST use type annotation.
* Use `| None` instead of `Optional`.
* Functions should that have many responsibilities, or longer than about 50
  lines, or nested deeply, should be split up into sub-functions.
* Code should use classes as much as possible. A class should have a single
  responsibility.
* Files that are large (over 500 lines) should be split into multiple
  files. Except for small classes, or private classes, each class should be
  in its own file.
* Classes that are almost entirely just data members should be dataclasses.
* All code in must have test coverage. Every Python file must have a matching
  test file (e.g. `my_module.py` must have a `test_my_module.py`).
* Test coverage must be thorough, every computed data point needs to be tested
  at least once, using values that are not default values.
* Strings should use single quotes, not double quotes. Double quotes are OK
  if the string contains apostrophes.
* Lines should not exceed 80 characters unless they contain strings that
  cannot be broken up, like URLs.
* Unused imports must be removed.
* All imports must be on the top of the file, unless there is a reason to
  import later.
* All functions must have docstrings, except in test files.
* The docstring for a function must have a one-line summary, then a blank
  line, then a more detailed description.
* The docstring for a function must have an Args section if there are any
  arguments, a Returns section if the function returns a value, and a Raises
  section if there are any exceptions that can be raised.
* After making code changes, apply Python formatting to the affected files,
  and run all the tests.
* Any identifier that describes milliseconds must have a `_ms` suffix.
* Functions that take multiple primitives of the same type must always be
  called with named arguments.
* Private functions may not be called from outside the class.
* `__main__.py` and `__init__.py` should be reserved for core elements that
  need to be exposed. Everything beyond that needs to be in separate files.
* Use guard clauses and early-outs to reduce nesting.

## System design

Read all `.md` files in the `design` directory and apply them when making
any code changes. Be sure to maintain this order:

1. `lf-structure.md`
2. `games.md`
3. `gametype-sm5.md`
4. `tdf-files.md`
5. `replay.md`
6. `video.md`
7. Everything else

## Code generation

* Data classes should use sqlalchemy and be as independent as possible of the
  actual SQL engine being used.
* TDF is not an acronym. Do not try to explain its meaning.
* Do not use absolute paths, even during tests. All path references must be
  relative.
* Any data point that can a finite set of values, for example team colors,
  teams, or player roles, should be described with an `enum.Enum` or a
  `dataclass` class with a list specific implementations. This is especially
  important for lists where each value has multiple pieces of data - for example
  a team color has its internal name, its display name, potentially a CSS
  name. There should not be hardcoded strings of specific values in the actual
  code outside the definition in the enum or class implementation.
* All Markdown must be properly formatted. Lines may not exceed 80 characters
  unless they cannot be broken down.

## Code structure

The code uses the following directories:

* **`model/`**: Model classes, enums, definitions.
    * **`model/constants/`**: Directory for files with enums, constants.
    * **`model/objects/`**: Directory for model objects - typically items that
      are created by importing data, and stored in databases.
    * **`model/gametypes/`**: Directory for files that are specific to certain
      game types, such as SM5. This should only be used for files that are
      very specific to a game type, like those with "sm5" in their name.
* **`replay/`**: Recreating the game state for a game, using events to play back
  all actions of the game.
* **`storage/`**: Code to interact with storage systems, like SQL databases.
* **`video/`**: Code to generate videos.
* **`importer/**: Code to import game data, such as from TDF files.

## Main command line tool interface

The command line tool has these arguments:

* --input_tdf: Filename of a TDF file. The data of this file will be read.
* --print_replay: Prints all replay events to the output.
* --state_at: Prints the complete game state given at the specific number of
  milliseconds into the game.
* --video_player: The name of the player to focus the video generation on.
* --video_state_at: Prints all UI elements given at the specific number of
  milliseconds into the game.
* --image-outdir: Folder to place all output images in. Defaults to the
  current directory.
* --image-at: Renders an image to be used at the specific number of
  milliseconds into the game. The image will be saved as a PNG file.
* --video_start_ms: Milliseconds into the game into which to start generating
  video frames for. Defaults to 0.
* --video_end_ms: Milliseconds into the game until which to generate video frames
  for. If not specified, will generate frames until 10 seconds after the game is
  over.
* --video_out: Filename of the video to generate from the images that were
  rendered.

## Persistent decisions

If any command or any conversation introduced important design decisions that will
apply to further decisions and are not currently captured in any existing document,
add them to the `design/additional_context.md`.

## Additional instructions

If there is an `private.AGENTS.md` file, read it entirely and follow all instructions.
