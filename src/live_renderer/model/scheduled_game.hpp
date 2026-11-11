/**
 * Data model representing a scheduled game in LF Live Renderer.
 *
 * This file provides the ScheduledGame class for tracking competition
 * schedule fixtures, participating team names and logos, timestamps,
 * stage identifiers, and completed scores with differential calculation.
 *
 * Usage example:
 *   live_renderer::ScheduledGame game("R1 M3 G2");
 *   game.SetTeamNames({"Tigers", "Lions"});
 *   game.SetScheduledStartTimeMs(1720612800000LL);
 *   game.SetScheduledEndTimeMs(1720614000000LL);
 */

#ifndef LIVE_RENDERER_MODEL_SCHEDULED_GAME_HPP_
#define LIVE_RENDERER_MODEL_SCHEDULED_GAME_HPP_

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace live_renderer {

/**
 * Model class for a scheduled game within an LF competition.
 *
 * Holds team names, logos, start/end timestamps, game name (e.g. R1 M3 G2),
 * optional round/match/game numbers, stage code, scores, and differential.
 */
class ScheduledGame {
public:
    /**
     * Constructs a default ScheduledGame.
     */
    ScheduledGame();

    /**
     * Constructs a ScheduledGame with initial properties.
     *
     * @param game_name Formatted game name string (e.g. 'R1 M3 G2').
     * @param team_names List of names of teams playing.
     * @param team_logos List of logo image URLs for teams playing.
     * @param scheduled_start_time_ms Scheduled start timestamp in ms.
     * @param scheduled_end_time_ms Scheduled end timestamp in ms.
     * @param round_number Optional integer round number.
     * @param match_number Optional integer match number.
     * @param game_number Optional integer game number.
     * @param stage_indicator Stage code prefix ('G', 'H', 'OT').
     * @param team_scores Optional scores for each team.
     */
    ScheduledGame(
        const std::string& game_name,
        const std::vector<std::string>& team_names = {},
        const std::vector<std::string>& team_logos = {},
        std::optional<int64_t> scheduled_start_time_ms = std::nullopt,
        std::optional<int64_t> scheduled_end_time_ms = std::nullopt,
        std::optional<int> round_number = std::nullopt,
        std::optional<int> match_number = std::nullopt,
        std::optional<int> game_number = std::nullopt,
        const std::string& stage_indicator = "G",
        std::optional<std::vector<int>> team_scores = std::nullopt);

    /**
     * Gets the game name string (e.g. 'R1 M3 G2').
     * @return Game name string.
     */
    const std::string& GetGameName() const;

    /**
     * Sets the game name string.
     * @param game_name Game name string.
     */
    void SetGameName(const std::string& game_name);

    /**
     * Gets the list of team names playing in this game.
     * @return Vector of team name strings.
     */
    const std::vector<std::string>& GetTeamNames() const;

    /**
     * Sets the list of team names playing in this game.
     * @param team_names Vector of team name strings.
     */
    void SetTeamNames(const std::vector<std::string>& team_names);

    /**
     * Adds a team name to the game.
     * @param team_name Team name string.
     */
    void AddTeamName(const std::string& team_name);

    /**
     * Gets the list of logo URLs for teams playing in this game.
     * @return Vector of logo URL strings.
     */
    const std::vector<std::string>& GetTeamLogos() const;

    /**
     * Sets the list of logo URLs for teams playing in this game.
     * @param team_logos Vector of logo URL strings.
     */
    void SetTeamLogos(const std::vector<std::string>& team_logos);

    /**
     * Adds a team logo URL to the game.
     * @param logo_url Logo URL string.
     */
    void AddTeamLogo(const std::string& logo_url);

    /**
     * Gets the scheduled start timestamp in milliseconds.
     * @return Optional int64_t start timestamp in ms.
     */
    const std::optional<int64_t>& GetScheduledStartTimeMs() const;

    /**
     * Sets the scheduled start timestamp in milliseconds.
     * @param scheduled_start_time_ms Start timestamp in ms.
     */
    void SetScheduledStartTimeMs(
        std::optional<int64_t> scheduled_start_time_ms);

    /**
     * Gets the scheduled end timestamp in milliseconds.
     * @return Optional int64_t end timestamp in ms.
     */
    const std::optional<int64_t>& GetScheduledEndTimeMs() const;

    /**
     * Sets the scheduled end timestamp in milliseconds.
     * @param scheduled_end_time_ms End timestamp in ms.
     */
    void SetScheduledEndTimeMs(std::optional<int64_t> scheduled_end_time_ms);

    /**
     * Gets the optional tournament round number.
     * @return Optional integer round number.
     */
    const std::optional<int>& GetRoundNumber() const;

    /**
     * Sets the optional tournament round number.
     * @param round_number Optional integer round number.
     */
    void SetRoundNumber(std::optional<int> round_number);

    /**
     * Gets the optional match number within the round.
     * @return Optional integer match number.
     */
    const std::optional<int>& GetMatchNumber() const;

    /**
     * Sets the optional match number within the round.
     * @param match_number Optional integer match number.
     */
    void SetMatchNumber(std::optional<int> match_number);

    /**
     * Gets the optional game number within the match.
     * @return Optional integer game number.
     */
    const std::optional<int>& GetGameNumber() const;

    /**
     * Sets the optional game number within the match.
     * @param game_number Optional integer game number.
     */
    void SetGameNumber(std::optional<int> game_number);

    /**
     * Gets the stage indicator prefix (e.g. 'G', 'H', 'OT').
     * @return Stage indicator string.
     */
    const std::string& GetStageIndicator() const;

    /**
     * Sets the stage indicator prefix (e.g. 'G', 'H', 'OT').
     * @param stage_indicator Stage indicator string.
     */
    void SetStageIndicator(const std::string& stage_indicator);

    /**
     * Gets the recorded scores for participating teams.
     * @return Optional vector of integer scores.
     */
    const std::optional<std::vector<int>>& GetTeamScores() const;

    /**
     * Sets the recorded scores for participating teams.
     * @param team_scores Optional vector of integer scores.
     */
    void SetTeamScores(std::optional<std::vector<int>> team_scores);

    /**
     * Checks whether the game has completed with recorded scores.
     * @return True if scores have been recorded, false otherwise.
     */
    bool IsComplete() const;

    /**
     * Computes the score differential between the first two teams.
     * @return Absolute score difference if >= 2 scores exist, or nullopt.
     */
    std::optional<int> GetScoreDifferential() const;

    /**
     * Formats round, match, and game numbers into a standard game name string.
     *
     * @param round_number Optional integer round number.
     * @param match_number Optional integer match number.
     * @param game_number Optional integer game number.
     * @param stage_indicator Stage prefix code (defaults to 'G').
     * @return Formatted game name string (e.g. 'R1 M3 G2').
     */
    static std::string FormatGameName(
        std::optional<int> round_number,
        std::optional<int> match_number,
        std::optional<int> game_number,
        const std::string& stage_indicator = "G");

    /**
     * Parses a game name string into round, match, game numbers, and stage.
     *
     * @param game_name Formatted game name string to parse.
     * @param out_round Output optional round number.
     * @param out_match Output optional match number.
     * @param out_game Output optional game number.
     * @param out_stage Output stage indicator string.
     */
    static void ParseGameName(
        const std::string& game_name,
        std::optional<int>& out_round,
        std::optional<int>& out_match,
        std::optional<int>& out_game,
        std::string& out_stage);

    /**
     * Checks equality with another ScheduledGame.
     * @param other The other ScheduledGame to compare against.
     * @return True if all fields match, false otherwise.
     */
    bool operator==(const ScheduledGame& other) const;

    /**
     * Checks inequality with another ScheduledGame.
     * @param other The other ScheduledGame to compare against.
     * @return True if any fields differ, false otherwise.
     */
    bool operator!=(const ScheduledGame& other) const;

private:
    std::string game_name_;
    std::vector<std::string> team_names_;
    std::vector<std::string> team_logos_;
    std::optional<int64_t> scheduled_start_time_ms_;
    std::optional<int64_t> scheduled_end_time_ms_;
    std::optional<int> round_number_;
    std::optional<int> match_number_;
    std::optional<int> game_number_;
    std::string stage_indicator_ = "G";
    std::optional<std::vector<int>> team_scores_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_MODEL_SCHEDULED_GAME_HPP_

