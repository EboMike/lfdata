# LFstats Data

The live renderer and some other parts of lfdata interact with the lfstats
server to fetch data from the global stats database.

All interactions are performed in code in the `lfstats/` subdirectory, with one
class acting as the main interface.

## General access

The main access point is `https://lfstats.com/api`. The API is described in
https://github.com/zmaniacz/lfstats/blob/main/docs/API.md.

The class should have a test mode option where it reads test data from local
storage instead of interacting with the actual website.

## API Key

Some RPC require an API key. The key needs to be provided with an additional
HTTP header:

```
Authorization: Bearer {api_key}
```

## Functionality

### Competitions

Competitions are defined in `design/competitions.md`.

API call: `/api/competitions`

Fetched by `LFStatsFetcher.fetch_competitions()`.
Returns a list of `CompetitionInfo` instances containing the `name` and `slug`
of each competition.

In test mode (`test_mode=True`), reads from `competitions.json` under
`tests/fixtures/lfstats/` (or custom `test_data_dir`).

### Competition team details

API call: `/api/competitions/{competition_slug}/stats`

Fetched by `LFStatsFetcher.fetch_competition_teams(competition_slug)`.
Returns a list of `CompetitionTeam` instances containing team slugs, names,
short names, logo URLs, and player rosters.

In test mode (`test_mode=True`), reads from `stats.json` or `teams.json` under
`tests/fixtures/lfstats/competitions/{competition_slug}/` (or custom
`test_data_dir`).

Returns information about all the players in the competition, and the teams
for each. This is a flat list, so information about teams will be duplicated
across all team members.

NOTE: This call requires an API key.

Relevant data to fetch:

```json
{
    "{competition_slug}": [
    {
      "ipl_id": "{player_entity_id}",
      "player_name": "{player_display_name}",
      "player_picture_url": "{player_profile_picture_url}",
      "team_name": "{team_name}",
      "team_logo_url": "{team_logo_url}",
    },
    ...
    ]
}
```

Note that URLs can be null. To get a list, use the team name as the primary
key and create a list from that. All team data, such as `team_logo_url`, should
be identical across all teams with the same primary key. Do not enforce it and
simply pick any random value for a given primary key to populate the list.

### Competition schedule

API call: `/api/competitions/{competition_slug}/schedule`

Fetched by `LFStatsFetcher.fetch_competition_schedule(competition_slug)`.
Returns a list of `ScheduledGame` instances with parsed round numbers, match
numbers, game numbers, stage indicators, start/end timestamps, team names,
team logos, scores, and differentials.

In test mode (`test_mode=True`), reads from local JSON fixtures located
under `tests/fixtures/lfstats/` (or custom `test_data_dir`).

### Lookup a player by entity ID
