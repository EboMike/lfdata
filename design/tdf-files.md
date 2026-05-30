# TDF File Description

## Overall structure

Use the file `assets/sm5_sanitized.tdf` as a reference for the actual structure
of a TDF file.

Each line in the file has a tab-delimited data point. Empty lines or lines with
semicolons should be ignored.

The first column is the type of data. The meaning of all other columns depends
on the data type, and also the game mode.

Some data types include a "time". This is the time to which the data point
applies. The time is given in milliseconds starting from the beginning of the game.


