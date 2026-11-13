#ifndef LIVE_RENDERER_STATE_LIVE_STATE_STORE_HPP_
#define LIVE_RENDERER_STATE_LIVE_STATE_STORE_HPP_

#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Player details provided by LFstats competition metadata.
 */
struct PlayerDetailsUpdate {
    std::string entity_id;
    std::string name;
    std::string picture_url;
    std::string team_name;
    std::string team_logo_url;
};

/**
 * @brief Thread-safe repository holding the live game state.
 *
 * Modified by the protocol parser / network thread upon receiving data events,
 * and read by the render thread as an immutable snapshot.
 */
class LiveStateStore {
public:
    LiveStateStore();
    ~LiveStateStore() = default;

    // Snapshot retrieval
    GameStateSnapshot GetSnapshot() const;

    // Mutator actions triggered by protocol events
    void ClearState();
    void ResetSession();
    void SetGameOver(int64_t timestamp_ms);
    void SetGameType(const std::string& type, int max_length_seconds);
    void SetGameStartTime(const std::string& timestamp_str);
    void SetCenterInfo(const std::string& center_id, const std::string& center_name);
    void SetBallCarrier(int player_id);

    void UpdateTeamDescription(int team_id, const std::string& name, const std::string& rgb, int dummy_player_id);
    void UpdateTeamScore(int team_id, int score);
    void UpdateTeamRankings(const std::vector<int>& team_ids);

    void UpdatePlayerDescription(int player_id, const std::string& name, const std::string& entity_id, int team_id, const std::string& role);
    void UpdatePlayerScore(int player_id, int score);
    void UpdatePlayerLives(int player_id, int lives);
    void UpdatePlayerShots(
        int player_id,
        int shots,
        int shots_fired = 0,
        int shots_hit = 0,
        const std::string& accuracy = ""
    );
    void UpdatePlayerMissiles(
        int player_id,
        int missiles,
        int missiles_fired = 0,
        int missiles_landed = 0
    );
    void UpdatePlayerNukesActivated(int player_id, int count);
    void UpdatePlayerNukesDetonated(int player_id, int count);
    void UpdatePlayerMedicHits(
        int player_id,
        const std::string& medic_hits
    );
    void UpdatePlayerSpecialPoints(int player_id, int sp);
    void UpdatePlayerHitpoints(int player_id, int hp);
    void UpdatePlayerState(int player_id, int state);
    void UpdatePlayerRapidFire(int player_id, bool has_rapid_fire);
    void UpdatePlayerGoals(int player_id, int goals);
    void UpdatePlayerAssists(int player_id, int assists);
    void UpdatePlayerBlocks(int player_id, int blocks);
    void UpdatePlayerSteals(int player_id, int steals);
    void UpdatePlayerRankings(int team_id, const std::vector<int>& player_ids);

    void UpdateTargetDescription(int target_id, const std::string& entity_id, const std::string& name, const std::string& rgb);
    void AddEventScrollerItem(int64_t timestamp_ms, const std::string& formatted_message);
    void AddImportantEventItem(
        int id,
        int64_t timestamp_ms,
        const std::string& formatted_message
    );

    void SetLatestEventTimeMs(int64_t time_ms);

    // Profile picture and competition player details
    void SetDefaultProfilePictureUrl(const std::string& url);
    std::string GetDefaultProfilePictureUrl() const;
    void UpdateCompetitionPlayerDetails(const std::vector<PlayerDetailsUpdate>& details);
    void UpdatePlayerPicture(int player_id, const std::string& picture_url);

    // Competition & schedule
    void SetCompetition(
        const std::string& name,
        const std::vector<ScheduledGame>& schedule);
    void SetCompetitionName(const std::string& name);
    void SetCompetitionSchedule(const std::vector<ScheduledGame>& schedule);
    void ClearCompetition();

private:
    void BumpVersionLocked();
    void RecomputeCompetitionValuesLocked();
    const PlayerDetailsUpdate* FindPlayerDetailsLocked(
        const std::string& entity_id, const std::string& name) const;

    mutable std::mutex mutex_;
    GameStateSnapshot state_;
    std::string default_profile_picture_url_;
    std::string competition_name_;
    std::vector<ScheduledGame> competition_schedule_;
    std::unordered_map<std::string, PlayerDetailsUpdate>
        competition_player_details_;
    std::unordered_map<std::string, PlayerDetailsUpdate>
        competition_player_details_by_name_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_STATE_LIVE_STATE_STORE_HPP_

