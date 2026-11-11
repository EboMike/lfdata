/**
 * Data model representing a competition team in LF Live Renderer.
 *
 * This file provides the CompetitionTeam class for storing participating
 * tournament teams, their short identifiers, logos, and player rosters.
 *
 * Usage example:
 *   live_renderer::CompetitionTeam team("tigers", "Thunder Tigers", "TIG");
 *   team.SetLogoUrl("https://example.com/tigers.png");
 *   team.AddPlayer("Alpha");
 */

#ifndef LIVE_RENDERER_MODEL_COMPETITION_TEAM_HPP_
#define LIVE_RENDERER_MODEL_COMPETITION_TEAM_HPP_

#include <string>
#include <vector>

namespace live_renderer {

/**
 * Model class for a team participating in an LF competition.
 *
 * Holds team slug identifier, display name, short abbreviation, logo URL,
 * and roster of participating players.
 */
class CompetitionTeam {
public:
    /**
     * Constructs a default CompetitionTeam.
     */
    CompetitionTeam();

    /**
     * Constructs a CompetitionTeam with initial properties.
     *
     * @param slug Unique slug identifier for the team.
     * @param name Full display name of the team.
     * @param short_name Short abbreviation (e.g. 3-4 characters).
     * @param logo_url Optional URL or file path for the team logo asset.
     * @param players Optional initial roster of player codenames.
     */
    CompetitionTeam(
        const std::string& slug,
        const std::string& name,
        const std::string& short_name,
        const std::string& logo_url = "",
        const std::vector<std::string>& players = {});

    /**
     * Gets the unique slug identifier of the team.
     * @return Team slug string.
     */
    const std::string& GetSlug() const;

    /**
     * Sets the unique slug identifier of the team.
     * @param slug Team slug string.
     */
    void SetSlug(const std::string& slug);

    /**
     * Gets the display name of the team.
     * @return Team name string.
     */
    const std::string& GetName() const;

    /**
     * Sets the display name of the team.
     * @param name Team name string.
     */
    void SetName(const std::string& name);

    /**
     * Gets the short abbreviation of the team.
     * @return Team short name string.
     */
    const std::string& GetShortName() const;

    /**
     * Sets the short abbreviation of the team.
     * @param short_name Team short name string.
     */
    void SetShortName(const std::string& short_name);

    /**
     * Gets the logo URL or asset path of the team.
     * @return Team logo URL string.
     */
    const std::string& GetLogoUrl() const;

    /**
     * Sets the logo URL or asset path of the team.
     * @param logo_url Team logo URL string.
     */
    void SetLogoUrl(const std::string& logo_url);

    /**
     * Gets the roster of players on the team.
     * @return Vector of player codenames.
     */
    const std::vector<std::string>& GetPlayers() const;

    /**
     * Sets the roster of players on the team.
     * @param players Vector of player codenames.
     */
    void SetPlayers(const std::vector<std::string>& players);

    /**
     * Adds a player codename to the team roster.
     * @param player Player codename string.
     */
    void AddPlayer(const std::string& player);

    /**
     * Removes a player codename from the team roster.
     * @param player Player codename string.
     * @return True if player was found and removed, false otherwise.
     */
    bool RemovePlayer(const std::string& player);

    /**
     * Checks whether a player codename is on the team roster.
     * @param player Player codename string.
     * @return True if present, false otherwise.
     */
    bool HasPlayer(const std::string& player) const;

    /**
     * Checks equality with another CompetitionTeam.
     * @param other The other CompetitionTeam to compare against.
     * @return True if all fields match, false otherwise.
     */
    bool operator==(const CompetitionTeam& other) const;

    /**
     * Checks inequality with another CompetitionTeam.
     * @param other The other CompetitionTeam to compare against.
     * @return True if any fields differ, false otherwise.
     */
    bool operator!=(const CompetitionTeam& other) const;

private:
    std::string slug_;
    std::string name_;
    std::string short_name_;
    std::string logo_url_;
    std::vector<std::string> players_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_MODEL_COMPETITION_TEAM_HPP_

