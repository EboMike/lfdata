#include "live_renderer/state/live_state_store.hpp"
#include <chrono>

namespace live_renderer {

static int64_t GetCurrentSteadyMillis() {
    auto now = std::chrono::steady_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
}

LiveStateStore::LiveStateStore() {
    state_.version = 1;
    state_.in_session = false;
    state_.game_over = false;
}

GameStateSnapshot LiveStateStore::GetSnapshot() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return state_;
}

void LiveStateStore::BumpVersionLocked() {
    state_.version++;
}

void LiveStateStore::ClearState() {
    std::lock_guard<std::mutex> lock(mutex_);
    const uint64_t next_version = state_.version + 1;
    state_ = GameStateSnapshot();
    state_.version = next_version;
    state_.in_session = false;
    state_.game_over = false;
}

void LiveStateStore::ResetSession() {
    std::lock_guard<std::mutex> lock(mutex_);
    const uint64_t next_version = state_.version + 1;
    state_ = GameStateSnapshot();
    state_.version = next_version;
    state_.in_session = true;
    state_.game_over = false;
    state_.game_start_time_local_ms = GetCurrentSteadyMillis();
}

void LiveStateStore::SetGameOver(int64_t timestamp_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.game_over = true;
    state_.latest_event_time_ms = timestamp_ms;
    BumpVersionLocked();
}

void LiveStateStore::SetGameType(const std::string& type, int max_length_seconds) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.game_type = type;
    state_.max_game_length_seconds = max_length_seconds;
    BumpVersionLocked();
}

void LiveStateStore::SetGameStartTime(const std::string& /*timestamp_str*/) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.in_session = true;
    state_.game_start_time_local_ms = GetCurrentSteadyMillis();
    BumpVersionLocked();
}

void LiveStateStore::SetCenterInfo(const std::string& center_id, const std::string& center_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.center_id = center_id;
    state_.center_name = center_name;
    BumpVersionLocked();
}

void LiveStateStore::SetBallCarrier(int player_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.ball_carrier_player_id = player_id;
    BumpVersionLocked();
}

void LiveStateStore::UpdateTeamDescription(int team_id, const std::string& name, const std::string& rgb, int dummy_player_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& team = state_.teams[team_id];
    team.id = team_id;
    team.name = name;
    team.rgb = rgb;
    team.dummy_player_id = dummy_player_id;
    if (dummy_player_id > 0) {
        state_.players[dummy_player_id].id = dummy_player_id;
        state_.players[dummy_player_id].team_id = team_id;
        state_.players[dummy_player_id].is_dummy = true;
    }
    BumpVersionLocked();
}

void LiveStateStore::UpdateTeamScore(int team_id, int score) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.teams[team_id].score = score;
    BumpVersionLocked();
}

void LiveStateStore::UpdateTeamRankings(const std::vector<int>& team_ids) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.team_rankings = team_ids;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerDescription(int player_id, const std::string& name, const std::string& entity_id, int team_id, const std::string& role) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& player = state_.players[player_id];
    player.id = player_id;
    player.name = name;
    player.entity_id = entity_id;
    player.team_id = team_id;
    player.role = role;

    // Maintain player list in team if not dummy
    if (!player.is_dummy && team_id > 0) {
        auto& p_ids = state_.teams[team_id].player_ids;
        bool exists = false;
        for (int id : p_ids) {
            if (id == player_id) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            p_ids.push_back(player_id);
        }
    }
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerScore(int player_id, int score) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].score = score;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerLives(int player_id, int lives) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].lives = lives;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerShots(int player_id, int shots) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].shots = shots;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerMissiles(int player_id, int missiles) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].missiles = missiles;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerSpecialPoints(int player_id, int sp) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].special_points = sp;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerHitpoints(int player_id, int hp) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].hitpoints = hp;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerState(int player_id, int pstate) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].state = pstate;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerRapidFire(int player_id, bool has_rapid_fire) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].has_rapid_fire = has_rapid_fire;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerGoals(int player_id, int goals) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].goals = goals;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerAssists(int player_id, int assists) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].assists = assists;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerBlocks(int player_id, int blocks) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].blocks = blocks;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerSteals(int player_id, int steals) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].steals = steals;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerRankings(int team_id, const std::vector<int>& player_ids) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.player_rankings_by_team[team_id] = player_ids;
    BumpVersionLocked();
}

void LiveStateStore::UpdateTargetDescription(int target_id, const std::string& entity_id, const std::string& name, const std::string& rgb) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& target = state_.targets[target_id];
    target.id = target_id;
    target.entity_id = entity_id;
    target.name = name;
    target.rgb = rgb;
    BumpVersionLocked();
}

void LiveStateStore::AddEventScrollerItem(int64_t timestamp_ms, const std::string& formatted_message) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.event_scroller.push_back({timestamp_ms, formatted_message});
    // Cap buffer to recent 200 items
    if (state_.event_scroller.size() > 200) {
        state_.event_scroller.erase(state_.event_scroller.begin(), state_.event_scroller.begin() + 50);
    }
    BumpVersionLocked();
}

void LiveStateStore::AddImportantEventItem(int64_t timestamp_ms, const std::string& formatted_message) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.important_events.push_back({timestamp_ms, formatted_message});
    if (state_.important_events.size() > 50) {
        state_.important_events.erase(state_.important_events.begin(), state_.important_events.begin() + 10);
    }
    BumpVersionLocked();
}

void LiveStateStore::SetLatestEventTimeMs(int64_t time_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.latest_event_time_ms = time_ms;
    if (time_ms > 0 && !state_.in_session) {
        state_.in_session = true;
        state_.game_start_time_local_ms = GetCurrentSteadyMillis() - time_ms;
    }
    BumpVersionLocked();
}

}  // namespace live_renderer

