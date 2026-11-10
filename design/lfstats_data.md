# LFstats Data

The live renderer and some other parts of ldata interact with the lfstats server
to fetch data from the global stats database.

All interactions are performed in code in the `lfstats/` subdirectory, with one
class acting as the main interface.

## General access

The main access point is `https://lfstats.com/api`. The API is described in
https://github.com/zmaniacz/lfstats/blob/main/docs/API.md.

The class should have a test mode option where it reads test data from local
storage instead of interacting with the actual website.

## Functionality

### Competitions

Competitions are defined in `design/competitions.md`.

### Competition schedule

API call: `/api/competitions/{competition_slug/schedule`

### Lookup a player by entity ID
