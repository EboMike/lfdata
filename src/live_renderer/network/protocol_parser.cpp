#include "live_renderer/network/protocol_parser.hpp"
#include <charconv>

namespace live_renderer {

ProtocolParser::ProtocolParser(LiveStateStore& store)
    : store_(store) {}

std::vector<std::string_view> ProtocolParser::SplitTabs(std::string_view s) {
    // Strip trailing \r or \n
    while (!s.empty() && (s.back() == '\r' || s.back() == '\n')) {
        s.remove_suffix(1);
    }
    std::vector<std::string_view> tokens;
    size_t start = 0;
    while (start <= s.size()) {
        size_t pos = s.find('\t', start);
        if (pos == std::string_view::npos) {
            tokens.push_back(s.substr(start));
            break;
        }
        tokens.push_back(s.substr(start, pos - start));
        start = pos + 1;
    }
    return tokens;
}

int ProtocolParser::ParseInt(std::string_view s, int default_val) {
    if (s.empty()) return default_val;
    int val = default_val;
    auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), val);
    return (ec == std::errc()) ? val : default_val;
}

int64_t ProtocolParser::ParseInt64(std::string_view s, int64_t default_val) {
    if (s.empty()) return default_val;
    int64_t val = default_val;
    auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), val);
    return (ec == std::errc()) ? val : default_val;
}

std::vector<int> ProtocolParser::ParseIntList(std::string_view s) {
    std::vector<int> list;
    if (s.empty()) return list;
    size_t start = 0;
    while (start <= s.size()) {
        size_t pos = s.find(',', start);
        std::string_view token = (pos == std::string_view::npos) ? s.substr(start) : s.substr(start, pos - start);
        if (!token.empty()) {
            list.push_back(ParseInt(token));
        }
        if (pos == std::string_view::npos) break;
        start = pos + 1;
    }
    return list;
}

bool ProtocolParser::ParseLine(std::string_view line) {
    auto tokens = SplitTabs(line);
    if (tokens.size() < 2) return false;

    int type = ParseInt(tokens[0]);
    int64_t time_ms = ParseInt64(tokens[1]);
    store_.SetLatestEventTimeMs(time_ms);

    switch (type) {
        case 1: { // Team score: type, time, team_id, score
            if (tokens.size() < 4) return false;
            store_.UpdateTeamScore(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 2: { // Game start time: type, time, YYYYMMDDHHMMSSmmm
            if (tokens.size() < 3) return false;
            store_.SetGameStartTime(std::string(tokens[2]));
            return true;
        }
        case 3: { // Player score: type, time, player_id, score
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerScore(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 4: { // Player lives: type, time, player_id, lives
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerLives(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 5: { // Player shots: type, time, player_id, shots
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerShots(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 6: { // Player special points: type, time, player_id, sp
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerSpecialPoints(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 7: { // Player hitpoints: type, time, player_id, hp
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerHitpoints(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 8: { // Event scroller message: type, time, message
            if (tokens.size() < 3) return false;
            store_.AddEventScrollerItem(time_ms, std::string(tokens[2]));
            return true;
        }
        case 9: { // Player state: type, time, player_id, state
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerState(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 10: { // Player missiles: type, time, player_id, missiles
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerMissiles(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 11: { // Player goals: type, time, player_id, goals
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerGoals(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 12: { // Player assists: type, time, player_id, assists
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerAssists(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 13: { // Player blocks: type, time, player_id, blocks
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerBlocks(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 14: { // Player steals: type, time, player_id, steals
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerSteals(ParseInt(tokens[2]), ParseInt(tokens[3]));
            return true;
        }
        case 15: { // Team description: type, time, team_id, name, rgb, dummy_player_id
            if (tokens.size() < 5) return false;
            int dummy_id = (tokens.size() >= 6) ? ParseInt(tokens[5]) : 0;
            store_.UpdateTeamDescription(ParseInt(tokens[2]), std::string(tokens[3]), std::string(tokens[4]), dummy_id);
            return true;
        }
        case 16: { // Player description: type, time, player_id, name, entity_id, team_id, role
            if (tokens.size() < 6) return false;
            std::string role = (tokens.size() >= 7) ? std::string(tokens[6]) : "";
            store_.UpdatePlayerDescription(ParseInt(tokens[2]), std::string(tokens[3]), std::string(tokens[4]), ParseInt(tokens[5]), role);
            return true;
        }
        case 17: { // Game type: type, time, game_type, max_length_seconds
            if (tokens.size() < 4) return false;
            store_.SetGameType(std::string(tokens[2]), ParseInt(tokens[3], 900));
            return true;
        }
        case 18: { // Ball carrier: type, time, player_id
            if (tokens.size() < 3) return false;
            store_.SetBallCarrier(ParseInt(tokens[2]));
            return true;
        }
        case 22: { // Base description: type, time, base_id, name, rgb
            if (tokens.size() < 5) return false;
            store_.UpdateTargetDescription(ParseInt(tokens[2]), "", std::string(tokens[3]), std::string(tokens[4]));
            return true;
        }
        case 23: { // Rapid fire: type, time, player_id, has_rapid_fire
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerRapidFire(ParseInt(tokens[2]), ParseInt(tokens[3]) != 0);
            return true;
        }
        case 24: { // PRESYNC_END: type, time
            return true;
        }
        case 25: { // Important event: type, time, message
            if (tokens.size() < 3) return false;
            store_.AddImportantEventItem(time_ms, std::string(tokens[2]));
            return true;
        }
        case 26: { // Player ranking: type, time, team_id, comma-separated player_ids
            if (tokens.size() < 4) return false;
            store_.UpdatePlayerRankings(ParseInt(tokens[2]), ParseIntList(tokens[3]));
            return true;
        }
        case 27: { // Team ranking: type, time, comma-separated team_ids
            if (tokens.size() < 3) return false;
            store_.UpdateTeamRankings(ParseIntList(tokens[2]));
            return true;
        }
        case 28: { // Center info: type, time, center_id, center_name
            if (tokens.size() < 4) return false;
            store_.SetCenterInfo(std::string(tokens[2]), std::string(tokens[3]));
            return true;
        }
        case 98: { // New game start: type, time
            store_.ResetSession();
            return true;
        }
        case 99: { // Game over: type, time
            store_.SetGameOver(time_ms);
            return true;
        }
        default:
            return false;
    }
}

}  // namespace live_renderer

