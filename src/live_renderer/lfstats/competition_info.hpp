/**
 * Data model for basic competition metadata from LFstats in LF Live Renderer.
 *
 * This file provides the CompetitionInfo class, which stores the display name
 * and unique URL/API slug identifier of a tournament competition.
 *
 * Usage example:
 *   live_renderer::CompetitionInfo info("Syracuse Trios 2026",
 *                                       "syracuse_trios_2026");
 *   std::cout << info.GetName() << " (" << info.GetSlug() << ")\n";
 */

#ifndef LIVE_RENDERER_LFSTATS_COMPETITION_INFO_HPP_
#define LIVE_RENDERER_LFSTATS_COMPETITION_INFO_HPP_

#include <string>

namespace live_renderer {

/**
 * Model class holding basic metadata describing an LFstats competition.
 *
 * Holds human-readable competition name and unique URL/API slug identifier.
 */
class CompetitionInfo {
public:
    /**
     * Constructs a default empty CompetitionInfo.
     */
    CompetitionInfo();

    /**
     * Constructs a CompetitionInfo with name and slug.
     *
     * @param name Full display name of the competition.
     * @param slug Unique URL/API slug identifier.
     */
    CompetitionInfo(const std::string& name, const std::string& slug);

    /**
     * Gets the human-readable display name of the competition.
     * @return Competition name string.
     */
    const std::string& GetName() const;

    /**
     * Sets the human-readable display name of the competition.
     * @param name Competition name string.
     */
    void SetName(const std::string& name);

    /**
     * Gets the unique URL/API slug identifier of the competition.
     * @return Competition slug string.
     */
    const std::string& GetSlug() const;

    /**
     * Sets the unique URL/API slug identifier of the competition.
     * @param slug Competition slug string.
     */
    void SetSlug(const std::string& slug);

    /**
     * Checks equality with another CompetitionInfo.
     * @param other The other CompetitionInfo instance to compare against.
     * @return True if name and slug match, false otherwise.
     */
    bool operator==(const CompetitionInfo& other) const;

    /**
     * Checks inequality with another CompetitionInfo.
     * @param other The other CompetitionInfo instance to compare against.
     * @return True if name or slug differs, false otherwise.
     */
    bool operator!=(const CompetitionInfo& other) const;

private:
    std::string name_;
    std::string slug_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_LFSTATS_COMPETITION_INFO_HPP_

