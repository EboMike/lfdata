#ifndef LIVE_RENDERER_STATE_GAME_STATE_SNAPSHOT_HPP_
#define LIVE_RENDERER_STATE_GAME_STATE_SNAPSHOT_HPP_

#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>

namespace live_renderer {

/**
 * @brief Representation of an individual player's live status and stats.
 */
struct PlayerSnapshot {
    int id = 0;
    std::string name;
    std::string entity_id;
    int team_id = 0;
    std::string role;
    int score = 0;
    int lives = 0;
    int shots = 0;
    int missiles = 0;
    int special_points = 0;
    int hitpoints = 1;
    int state = 0;             // 0=Up, 2=Resettable, 3=Down, 4=Dead
    bool has_rapid_fire = false;
    int goals = 0;
    int assists = 0;
    int blocks = 0;            // Also called zaps
    int steals = 0;
    int clears = 0;
    bool is_dummy = false;
};

/**
 * @brief Representation of a team's live status and stats.
 */
struct TeamSnapshot {
    int id = 0;
    std::string name;
    std::string rgb = "#ffffff";
    int score = 0;
    int dummy_player_id = 0;
    std::vector<int> player_ids;
};

/**
 * @brief Representation of a target entity (base, etc.).
 */
struct TargetSnapshot {
    int id = 0;
    std::string entity_id;
    std::string name;
    std::string rgb = "#ffffff";
};

/**
 * @brief Representation of an individual event log item.
 */
struct EventItem {
    int64_t timestamp_ms = 0;
    std::string formatted_message;
};

/**
 * @brief Thread-safe immutable snapshot of the entire game session state at a point in time.
 */
struct GameStateSnapshot {
    uint64_t version = 0;
    bool in_session = false;
    bool game_over = false;
    std::string game_type = "SM5";
    int max_game_length_seconds = 900;
    int64_t game_start_time_local_ms = 0;  // Local monotonic steady clock MS when start was received
    int64_t latest_event_time_ms = 0;
    int ball_carrier_player_id = 0;
    std::string center_id;
    std::string center_name;

    std::unordered_map<int, TeamSnapshot> teams;
    std::unordered_map<int, PlayerSnapshot> players;
    std::unordered_map<int, TargetSnapshot> targets;
    std::vector<int> team_rankings;
    std::unordered_map<int, std::vector<int>> player_rankings_by_team;
    std::vector<EventItem> event_scroller;
    std::vector<EventItem> important_events;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_STATE_GAME_STATE_SNAPSHOT_HPP_

