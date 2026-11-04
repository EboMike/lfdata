#ifndef LIVE_RENDERER_COMPONENTS_SCORECARD_HELPER_HPP_
#define LIVE_RENDERER_COMPONENTS_SCORECARD_HELPER_HPP_

#include <array>
#include <vector>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

enum class PlayerSortOrder {
    Index,
    Ranking
};

enum class TeamSortOrder {
    Index,
    Ranking
};

/**
 * @brief Helper functions for sorting teams, players, and formatting scorecard rows.
 */
class ScorecardHelper {
public:
    static std::vector<int> GetSortedTeamIds(
        const GameStateSnapshot& state,
        TeamSortOrder sort_order);

    static std::vector<int> GetSortedPlayerIds(
        const GameStateSnapshot& state,
        int team_id,
        PlayerSortOrder sort_order,
        bool add_totals);

    /**
     * @brief Determines the row text color according to live_renderer.md:
     * - Default: team RGB
     * - Dead / out of lives: "#808080" (gray)
     * - Down / resettable: darker tone of team RGB (e.g. 50% multiplier)
     */
    static std::string GetRowTextColor(
        const PlayerSnapshot& player,
        const std::string& team_rgb);

    /**
     * @brief Computes RGBA color multipliers to tint an image/movie with team
     *        color according to tint_team_color (0.0 to 1.0).
     */
    static std::array<float, 4> ComputeTeamTint(
        const std::string& team_rgb,
        float tint_amount);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_SCORECARD_HELPER_HPP_

