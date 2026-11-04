#include "live_renderer/components/scorecard_helper.hpp"
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace live_renderer {

static std::string DarkenHexColor(const std::string& hex) {
    if (hex.size() < 7 || hex[0] != '#') return hex;
    int r = 0, g = 0, b = 0;
    try {
        r = std::stoi(hex.substr(1, 2), nullptr, 16);
        g = std::stoi(hex.substr(3, 2), nullptr, 16);
        b = std::stoi(hex.substr(5, 2), nullptr, 16);
    } catch (...) {
        return hex;
    }
    r = r / 2;
    g = g / 2;
    b = b / 2;
    std::ostringstream oss;
    oss << "#" << std::hex << std::setfill('0')
        << std::setw(2) << r
        << std::setw(2) << g
        << std::setw(2) << b;
    return oss.str();
}

std::vector<int> ScorecardHelper::GetSortedTeamIds(
    const GameStateSnapshot& state,
    TeamSortOrder sort_order) {
    std::vector<int> team_ids;
    for (const auto& [id, _] : state.teams) {
        team_ids.push_back(id);
    }

    if (sort_order == TeamSortOrder::Ranking && !state.team_rankings.empty()) {
        std::vector<int> ranked;
        for (int id : state.team_rankings) {
            if (state.teams.contains(id)) {
                ranked.push_back(id);
            }
        }
        for (int id : team_ids) {
            if (std::find(ranked.begin(), ranked.end(), id) == ranked.end()) {
                ranked.push_back(id);
            }
        }
        return ranked;
    }

    std::sort(team_ids.begin(), team_ids.end());
    return team_ids;
}

std::vector<int> ScorecardHelper::GetSortedPlayerIds(
    const GameStateSnapshot& state,
    int team_id,
    PlayerSortOrder sort_order,
    bool add_totals) {
    std::vector<int> players;
    auto it = state.teams.find(team_id);
    if (it == state.teams.end()) return players;

    const auto& team = it->second;
    players = team.player_ids;

    if (sort_order == PlayerSortOrder::Ranking) {
        auto rank_it = state.player_rankings_by_team.find(team_id);
        if (rank_it != state.player_rankings_by_team.end() && !rank_it->second.empty()) {
            std::vector<int> ranked;
            for (int id : rank_it->second) {
                if (std::find(players.begin(), players.end(), id) != players.end()) {
                    ranked.push_back(id);
                }
            }
            for (int id : players) {
                if (std::find(ranked.begin(), ranked.end(), id) == ranked.end()) {
                    ranked.push_back(id);
                }
            }
            players = ranked;
        }
    } else {
        std::sort(players.begin(), players.end());
    }

    if (add_totals && team.dummy_player_id > 0) {
        players.push_back(team.dummy_player_id);
    }

    return players;
}

std::string ScorecardHelper::GetRowTextColor(
    const PlayerSnapshot& player,
    const std::string& team_rgb) {
    if (player.is_dummy) {
        return team_rgb;
    }
    // Out of lives or Dead (state 4)
    if (player.lives <= 0 || player.state == 4) {
        return "#808080";
    }
    // Down (state 3) or Resettable (state 2)
    if (player.state == 3 || player.state == 2) {
        return DarkenHexColor(team_rgb);
    }
    // Normal active player
    return team_rgb;
}

std::array<float, 4> ScorecardHelper::ComputeTeamTint(
    const std::string& team_rgb,
    float tint_amount) {
    if (tint_amount <= 0.0f) {
        return {1.0f, 1.0f, 1.0f, 1.0f};
    }
    const float t = std::clamp(tint_amount, 0.0f, 1.0f);
    if (team_rgb.size() < 7 || team_rgb[0] != '#') {
        return {1.0f, 1.0f, 1.0f, 1.0f};
    }
    int r = 255;
    int g = 255;
    int b = 255;
    try {
        r = std::stoi(team_rgb.substr(1, 2), nullptr, 16);
        g = std::stoi(team_rgb.substr(3, 2), nullptr, 16);
        b = std::stoi(team_rgb.substr(5, 2), nullptr, 16);
    } catch (...) {
        return {1.0f, 1.0f, 1.0f, 1.0f};
    }
    const float team_r = r / 255.0f;
    const float team_g = g / 255.0f;
    const float team_b = b / 255.0f;

    return {
        1.0f + t * (team_r - 1.0f),
        1.0f + t * (team_g - 1.0f),
        1.0f + t * (team_b - 1.0f),
        1.0f
    };
}

std::array<float, 4> ScorecardHelper::ParseHexColor(
    const std::string& hex,
    float default_alpha) {
    if (hex.empty() || hex[0] != '#') {
        return {1.0f, 1.0f, 1.0f, default_alpha};
    }
    try {
        if (hex.size() == 7) {
            int r = std::stoi(hex.substr(1, 2), nullptr, 16);
            int g = std::stoi(hex.substr(3, 2), nullptr, 16);
            int b = std::stoi(hex.substr(5, 2), nullptr, 16);
            return {r / 255.0f, g / 255.0f, b / 255.0f, default_alpha};
        }
        if (hex.size() == 9) {
            int r = std::stoi(hex.substr(1, 2), nullptr, 16);
            int g = std::stoi(hex.substr(3, 2), nullptr, 16);
            int b = std::stoi(hex.substr(5, 2), nullptr, 16);
            int a = std::stoi(hex.substr(7, 2), nullptr, 16);
            return {r / 255.0f, g / 255.0f, b / 255.0f, a / 255.0f};
        }
    } catch (...) {
        return {1.0f, 1.0f, 1.0f, default_alpha};
    }
    return {1.0f, 1.0f, 1.0f, default_alpha};
}

}  // namespace live_renderer

