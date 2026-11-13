#include "live_renderer/state/live_state_store.hpp"
#include <algorithm>
#include <chrono>
#include "live_renderer/config/global_config.hpp"

namespace live_renderer {

static int64_t GetCurrentSteadyMillis() {
    auto now = std::chrono::steady_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
}

static std::string NormalizeEntityId(const std::string& id) {
    if (id.empty()) return "";
    size_t start = 0;
    while (start < id.size() &&
           (id[start] == '#' || id[start] == '@' || id[start] == ' ')) {
        start++;
    }
    return id.substr(start);
}

static std::string ToLowerTrim(const std::string& str) {
    if (str.empty()) return "";
    size_t start = str.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    size_t end = str.find_last_not_of(" \t\r\n");
    std::string trimmed = str.substr(start, end - start + 1);
    for (char& c : trimmed) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return trimmed;
}

LiveStateStore::LiveStateStore()
    : default_profile_picture_url_(kDefaultProfilePictureUrl) {
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
    RecomputeCompetitionValuesLocked();
}

void LiveStateStore::ResetSession() {
    std::lock_guard<std::mutex> lock(mutex_);
    const uint64_t next_version = state_.version + 1;
    state_ = GameStateSnapshot();
    state_.version = next_version;
    state_.in_session = true;
    state_.game_over = false;
    state_.game_start_time_local_ms = GetCurrentSteadyMillis();
    RecomputeCompetitionValuesLocked();
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

void LiveStateStore::UpdateTeamDescription(
    int team_id,
    const std::string& name,
    const std::string& rgb,
    int dummy_player_id) {
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
        auto& p_ids = team.player_ids;
        p_ids.erase(
            std::remove(p_ids.begin(), p_ids.end(), dummy_player_id),
            p_ids.end());
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

const PlayerDetailsUpdate* LiveStateStore::FindPlayerDetailsLocked(
    const std::string& entity_id, const std::string& name) const {
    if (!entity_id.empty()) {
        auto it = competition_player_details_.find(entity_id);
        if (it != competition_player_details_.end()) return &it->second;

        std::string norm = NormalizeEntityId(entity_id);
        if (!norm.empty()) {
            it = competition_player_details_.find(norm);
            if (it != competition_player_details_.end()) return &it->second;

            auto dash = norm.rfind('-');
            if (dash != std::string::npos && dash + 1 < norm.size()) {
                it = competition_player_details_.find(norm.substr(dash + 1));
                if (it != competition_player_details_.end()) return &it->second;
            }
        }
    }

    if (!name.empty()) {
        std::string lower_name = ToLowerTrim(name);
        auto it = competition_player_details_by_name_.find(lower_name);
        if (it != competition_player_details_by_name_.end()) return &it->second;
    }

    return nullptr;
}

void LiveStateStore::UpdatePlayerDescription(
    int player_id,
    const std::string& name,
    const std::string& entity_id,
    int team_id,
    const std::string& role) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& player = state_.players[player_id];
    player.id = player_id;
    player.name = name;
    player.entity_id = entity_id;
    player.team_id = team_id;
    player.role = role;

    // Check if competition details provide picture or team metadata
    const auto* match = FindPlayerDetailsLocked(entity_id, name);
    if (match) {
        player.picture_url = match->picture_url.empty()
            ? default_profile_picture_url_
            : match->picture_url;
        if (!match->team_name.empty()) {
            player.team_name = match->team_name;
        }
        if (!match->team_logo_url.empty()) {
            player.team_logo_url = match->team_logo_url;
        }
    } else if (player.picture_url.empty()) {
        player.picture_url = default_profile_picture_url_;
    }

    if (team_id > 0 && state_.teams[team_id].dummy_player_id == player_id) {
        player.is_dummy = true;
    }

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

void LiveStateStore::UpdatePlayerShots(
    int player_id,
    int shots,
    int shots_fired,
    int shots_hit,
    const std::string& accuracy) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& p = state_.players[player_id];
    p.shots = shots;
    if (shots_fired > 0 || shots_hit > 0 || !accuracy.empty()) {
        p.shots_fired = shots_fired;
        p.shots_hit = shots_hit;
        p.accuracy = accuracy;
    }
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerMissiles(
    int player_id,
    int missiles,
    int missiles_fired,
    int missiles_landed) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& p = state_.players[player_id];
    p.missiles = missiles;
    if (missiles_fired > 0 || missiles_landed > 0) {
        p.missiles_fired = missiles_fired;
        p.missiles_landed = missiles_landed;
    }
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerNukesActivated(int player_id, int count) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].nukes_activated = count;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerNukesDetonated(int player_id, int count) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].nukes_detonated = count;
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerMedicHits(
    int player_id,
    const std::string& medic_hits) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].medic_hits = medic_hits;
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

void LiveStateStore::AddImportantEventItem(
    int id,
    int64_t timestamp_ms,
    const std::string& formatted_message
) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& item : state_.important_events) {
        if (item.id == id) {
            item.timestamp_ms = timestamp_ms;
            item.formatted_message = formatted_message;
            BumpVersionLocked();
            return;
        }
    }
    state_.important_events.push_back({id, timestamp_ms, formatted_message});
    if (state_.important_events.size() > 50) {
        state_.important_events.erase(
            state_.important_events.begin(),
            state_.important_events.begin() + 10
        );
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

void LiveStateStore::SetDefaultProfilePictureUrl(const std::string& url) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::string old_default = default_profile_picture_url_;
    default_profile_picture_url_ = url;
    for (auto& [pid, player] : state_.players) {
        if (player.picture_url.empty() || player.picture_url == old_default) {
            player.picture_url = default_profile_picture_url_;
        }
    }
    BumpVersionLocked();
}

std::string LiveStateStore::GetDefaultProfilePictureUrl() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return default_profile_picture_url_;
}

void LiveStateStore::UpdateCompetitionPlayerDetails(
    const std::vector<PlayerDetailsUpdate>& details) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (const auto& d : details) {
        if (!d.entity_id.empty()) {
            competition_player_details_[d.entity_id] = d;
            std::string norm = NormalizeEntityId(d.entity_id);
            if (!norm.empty()) {
                competition_player_details_[norm] = d;
                auto dash = norm.rfind('-');
                if (dash != std::string::npos && dash + 1 < norm.size()) {
                    competition_player_details_[norm.substr(dash + 1)] = d;
                }
            }
        }
        if (!d.name.empty()) {
            std::string lower_name = ToLowerTrim(d.name);
            if (!lower_name.empty()) {
                competition_player_details_by_name_[lower_name] = d;
            }
        }
    }

    // Apply updates to existing active players
    for (auto& [pid, player] : state_.players) {
        if (player.is_dummy) continue;
        const auto* match =
            FindPlayerDetailsLocked(player.entity_id, player.name);
        if (match) {
            player.picture_url = match->picture_url.empty()
                ? default_profile_picture_url_
                : match->picture_url;
            if (!match->team_name.empty()) {
                player.team_name = match->team_name;
            }
            if (!match->team_logo_url.empty()) {
                player.team_logo_url = match->team_logo_url;
            }
        } else if (player.picture_url.empty()) {
            player.picture_url = default_profile_picture_url_;
        }
    }
    BumpVersionLocked();
}

void LiveStateStore::UpdatePlayerPicture(
    int player_id, const std::string& picture_url) {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.players[player_id].picture_url = picture_url.empty()
        ? default_profile_picture_url_
        : picture_url;
    BumpVersionLocked();
}

void LiveStateStore::SetCompetition(
    const std::string& name,
    const std::vector<ScheduledGame>& schedule) {
    std::lock_guard<std::mutex> lock(mutex_);
    competition_name_ = name;
    competition_schedule_ = schedule;
    RecomputeCompetitionValuesLocked();
    BumpVersionLocked();
}

void LiveStateStore::SetCompetitionName(const std::string& name) {
    std::lock_guard<std::mutex> lock(mutex_);
    competition_name_ = name;
    RecomputeCompetitionValuesLocked();
    BumpVersionLocked();
}

void LiveStateStore::SetCompetitionSchedule(
    const std::vector<ScheduledGame>& schedule) {
    std::lock_guard<std::mutex> lock(mutex_);
    competition_schedule_ = schedule;
    RecomputeCompetitionValuesLocked();
    BumpVersionLocked();
}

void LiveStateStore::ClearCompetition() {
    std::lock_guard<std::mutex> lock(mutex_);
    competition_name_.clear();
    competition_schedule_.clear();
    RecomputeCompetitionValuesLocked();
    BumpVersionLocked();
}

void LiveStateStore::RecomputeCompetitionValuesLocked() {
    state_.competition_name = competition_name_;
    state_.competition_schedule = competition_schedule_;

    if (competition_schedule_.empty()) {
        state_.competition_team_1_name.clear();
        state_.competition_team_2_name.clear();
        state_.next_scheduled_game_team_1_name.clear();
        state_.next_scheduled_game_team_2_name.clear();
        return;
    }

    auto sorted_schedule = competition_schedule_;
    std::stable_sort(
        sorted_schedule.begin(),
        sorted_schedule.end(),
        [](const ScheduledGame& a, const ScheduledGame& b) {
            int64_t a_time = a.GetScheduledStartTimeMs().value_or(0);
            int64_t b_time = b.GetScheduledStartTimeMs().value_or(0);
            return a_time < b_time;
        });

    size_t current_idx = static_cast<size_t>(-1);
    for (size_t i = 0; i < sorted_schedule.size(); ++i) {
        if (!sorted_schedule[i].IsComplete()) {
            current_idx = i;
            break;
        }
    }

    if (current_idx != static_cast<size_t>(-1)) {
        const auto& current_game = sorted_schedule[current_idx];
        const auto& cur_teams = current_game.GetTeamNames();
        state_.competition_team_1_name =
            cur_teams.size() > 0 ? cur_teams[0] : "";
        state_.competition_team_2_name =
            cur_teams.size() > 1 ? cur_teams[1] : "";

        if (current_idx + 1 < sorted_schedule.size()) {
            const auto& next_game = sorted_schedule[current_idx + 1];
            const auto& next_teams = next_game.GetTeamNames();
            state_.next_scheduled_game_team_1_name =
                next_teams.size() > 0 ? next_teams[0] : "";
            state_.next_scheduled_game_team_2_name =
                next_teams.size() > 1 ? next_teams[1] : "";
        } else {
            state_.next_scheduled_game_team_1_name.clear();
            state_.next_scheduled_game_team_2_name.clear();
        }
    } else {
        state_.competition_team_1_name.clear();
        state_.competition_team_2_name.clear();
        state_.next_scheduled_game_team_1_name.clear();
        state_.next_scheduled_game_team_2_name.clear();
    }
}

}  // namespace live_renderer

