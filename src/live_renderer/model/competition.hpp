/**
 * Data model representing a competition event in LF Live Renderer.
 *
 * This file provides the Competition class, which represents an LF tournament
 * or competition event occurring at a specific site within a given timeframe.
 * It manages participating teams and the complete match schedule.
 *
 * Usage example:
 *   live_renderer::Competition comp("LF World Championships 2026");
 *   comp.SetSite("Brisbane");
 *   comp.SetSlug("lf_worlds_2026");
 *   comp.AddTeam(live_renderer::CompetitionTeam("tigers", "Tigers", "TIG"));
 *   comp.AddScheduledGame(live_renderer::ScheduledGame("R1 M1 G1"));
 */

#ifndef LIVE_RENDERER_MODEL_COMPETITION_HPP_
#define LIVE_RENDERER_MODEL_COMPETITION_HPP_

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "live_renderer/model/competition_team.hpp"
#include "live_renderer/model/scheduled_game.hpp"

namespace live_renderer {

/**
 * Model class for an LF tournament or competition event.
 *
 * Holds competition name, slug, site/venue, timeframe start and end
 * timestamps in milliseconds, participating teams, and match schedule.
 */
class Competition {
public:
    /**
     * Constructs a default Competition.
     */
    Competition();

    /**
     * Constructs a Competition with initial properties.
     *
     * @param name Full display name of the competition.
     * @param slug Unique slug identifier for lookup/URLs.
     * @param site Location or venue name where event occurs.
     * @param start_time_ms Start timestamp in milliseconds.
     * @param end_time_ms End timestamp in milliseconds.
     * @param teams List of participating teams.
     * @param schedule List of scheduled games.
     */
    Competition(
        const std::string& name,
        const std::string& slug = "",
        const std::string& site = "",
        std::optional<int64_t> start_time_ms = std::nullopt,
        std::optional<int64_t> end_time_ms = std::nullopt,
        const std::vector<CompetitionTeam>& teams = {},
        const std::vector<ScheduledGame>& schedule = {});

    /**
     * Gets the full display name of the competition.
     * @return Competition name string.
     */
    const std::string& GetName() const;

    /**
     * Sets the full display name of the competition.
     * @param name Competition name string.
     */
    void SetName(const std::string& name);

    /**
     * Gets the unique slug identifier of the competition.
     * @return Competition slug string.
     */
    const std::string& GetSlug() const;

    /**
     * Sets the unique slug identifier of the competition.
     * @param slug Competition slug string.
     */
    void SetSlug(const std::string& slug);

    /**
     * Gets the site or venue name of the competition.
     * @return Competition site string.
     */
    const std::string& GetSite() const;

    /**
     * Sets the site or venue name of the competition.
     * @param site Competition site string.
     */
    void SetSite(const std::string& site);

    /**
     * Gets the start timestamp of the competition in milliseconds.
     * @return Optional int64_t start timestamp in ms.
     */
    const std::optional<int64_t>& GetStartTimeMs() const;

    /**
     * Sets the start timestamp of the competition in milliseconds.
     * @param start_time_ms Start timestamp in ms.
     */
    void SetStartTimeMs(std::optional<int64_t> start_time_ms);

    /**
     * Gets the end timestamp of the competition in milliseconds.
     * @return Optional int64_t end timestamp in ms.
     */
    const std::optional<int64_t>& GetEndTimeMs() const;

    /**
     * Sets the end timestamp of the competition in milliseconds.
     * @param end_time_ms End timestamp in ms.
     */
    void SetEndTimeMs(std::optional<int64_t> end_time_ms);

    /**
     * Gets the list of participating teams in the competition.
     * @return Vector of CompetitionTeam instances.
     */
    const std::vector<CompetitionTeam>& GetTeams() const;

    /**
     * Sets the list of participating teams in the competition.
     * @param teams Vector of CompetitionTeam instances.
     */
    void SetTeams(const std::vector<CompetitionTeam>& teams);

    /**
     * Adds a team to the competition.
     * @param team CompetitionTeam instance to add.
     */
    void AddTeam(const CompetitionTeam& team);

    /**
     * Removes a team from the competition by its slug.
     * @param slug Team slug string.
     * @return True if team was found and removed, false otherwise.
     */
    bool RemoveTeam(const std::string& slug);

    /**
     * Finds a participating team by its slug.
     * @param slug Team slug string.
     * @return Pointer to team if found, nullptr otherwise.
     */
    const CompetitionTeam* FindTeam(const std::string& slug) const;

    /**
     * Finds a mutable participating team by its slug.
     * @param slug Team slug string.
     * @return Pointer to mutable team if found, nullptr otherwise.
     */
    CompetitionTeam* FindTeam(const std::string& slug);

    /**
     * Checks whether a team with the given slug is in the competition.
     * @param slug Team slug string.
     * @return True if present, false otherwise.
     */
    bool HasTeam(const std::string& slug) const;

    /**
     * Gets the match schedule of the competition.
     * @return Vector of ScheduledGame instances.
     */
    const std::vector<ScheduledGame>& GetSchedule() const;

    /**
     * Sets the match schedule of the competition.
     * @param schedule Vector of ScheduledGame instances.
     */
    void SetSchedule(const std::vector<ScheduledGame>& schedule);

    /**
     * Adds a scheduled game to the competition schedule.
     * @param game ScheduledGame instance to add.
     */
    void AddScheduledGame(const ScheduledGame& game);

    /**
     * Removes a scheduled game by its index in the schedule.
     * @param index Zero-based index of the scheduled game.
     * @return True if index is valid and game removed, false otherwise.
     */
    bool RemoveScheduledGame(size_t index);

    /**
     * Finds a scheduled game by its game name (e.g. 'R1 M3 G2').
     * @param game_name Game name string to search for.
     * @return Pointer to scheduled game if found, nullptr otherwise.
     */
    const ScheduledGame* FindScheduledGame(
        const std::string& game_name) const;

    /**
     * Finds a mutable scheduled game by its game name (e.g. 'R1 M3 G2').
     * @param game_name Game name string to search for.
     * @return Pointer to mutable scheduled game if found, nullptr otherwise.
     */
    ScheduledGame* FindScheduledGame(const std::string& game_name);

    /**
     * Retrieves all scheduled games in which a given team participates.
     * @param team_name Name of the team to filter by.
     * @return Vector of pointers to matching ScheduledGame objects.
     */
    std::vector<const ScheduledGame*> GetGamesForTeam(
        const std::string& team_name) const;

    /**
     * Gets the total number of games in the schedule.
     * @return Total scheduled games count.
     */
    size_t GetTotalGamesCount() const;

    /**
     * Gets the number of completed games (with scores recorded) in schedule.
     * @return Completed scheduled games count.
     */
    size_t GetCompletedGamesCount() const;

    /**
     * Checks equality with another Competition.
     * @param other The other Competition to compare against.
     * @return True if all fields match, false otherwise.
     */
    bool operator==(const Competition& other) const;

    /**
     * Checks inequality with another Competition.
     * @param other The other Competition to compare against.
     * @return True if any fields differ, false otherwise.
     */
    bool operator!=(const Competition& other) const;

private:
    std::string name_;
    std::string slug_;
    std::string site_;
    std::optional<int64_t> start_time_ms_;
    std::optional<int64_t> end_time_ms_;
    std::vector<CompetitionTeam> teams_;
    std::vector<ScheduledGame> schedule_;
};

/**
 * Convenience alias for Competition.
 */
using Tournament = Competition;

}  // namespace live_renderer

#endif  // LIVE_RENDERER_MODEL_COMPETITION_HPP_

