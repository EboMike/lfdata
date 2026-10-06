"""CLI module entry point for running the Color Correction Editor.

This module allows launching the application with
`python -m lfdata.color_correction`.

Usage example:
    $ python -m lfdata.color_correction
"""

from lfdata.color_correction.editor import main


if __name__ == '__main__':
    main()
