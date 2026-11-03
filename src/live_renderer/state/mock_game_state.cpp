#include "live_renderer/state/mock_game_state.hpp"
#include <chrono>

namespace live_renderer {

static int64_t GetCurrentSteadyMillis() {
    auto now = std::chrono::steady_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
}

GameStateSnapshot MockGameState::CreateMockSM5State() {
    GameStateSnapshot s;
    s.version = 100;
    s.in_session = true;
    s.game_over = false;
    s.game_type = "SM5";
    s.max_game_length_seconds = 900;
    s.game_start_time_local_ms = GetCurrentSteadyMillis() - 245000; // ~4m 5s into game
    s.latest_event_time_ms = 245000;
    s.center_id = "4-43";
    s.center_name = "Loveland";

    // Team 1: Fire (#FF5000)
    TeamSnapshot t1;
    t1.id = 1;
    t1.name = "Fire";
    t1.rgb = "#FF5000";
    t1.score = 24500;
    t1.dummy_player_id = 101;
    t1.player_ids = {11, 12, 13, 14, 15};
    s.teams[1] = t1;

    // Team 2: Earth (#A0FF00)
    TeamSnapshot t2;
    t2.id = 2;
    t2.name = "Earth";
    t2.rgb = "#A0FF00";
    t2.score = 21800;
    t2.dummy_player_id = 102;
    t2.player_ids = {21, 22, 23, 24, 25};
    s.teams[2] = t2;

    s.team_rankings = {1, 2};

    // Fire Players
    s.players[11] = {11, "AlphaCommander", "#101", 1, "commander", 8200, 12, 45, 3, 20, 2, 0, false};
    s.players[12] = {12, "FireHeavy",     "#102", 1, "heavy",     6400, 8,  25, 2, 0,  1, 0, true}; // Rapid fire!
    s.players[13] = {13, "BlazeScout",     "#103", 1, "scout",     4100, 14, 30, 0, 15, 1, 3, false}; // Down
    s.players[14] = {14, "PhoenixMedic",   "#104", 1, "medic",     3300, 18, 12, 0, 10, 1, 0, false};
    s.players[15] = {15, "PyroAmmo",       "#105", 1, "ammo",      2500, 0,  0,  0, 0,  0, 4, false}; // Eliminated

    // Fire Dummy Player
    s.players[101] = {101, "", "", 1, "", 24500, 52, 112, 5, 45, 5, 0, false, 0, 0, 0, 0, 0, true};

    // Earth Players
    s.players[21] = {21, "TerraCommander", "#201", 2, "commander", 7500, 10, 40, 1, 15, 1, 0, false};
    s.players[22] = {22, "StoneHeavy",     "#202", 2, "heavy",     5800, 6,  18, 1, 0,  1, 2, false}; // Resettable
    s.players[23] = {23, "MossScout",      "#203", 2, "scout",     4600, 15, 35, 0, 0,  1, 0, false};
    s.players[24] = {24, "FloraMedic",     "#204", 2, "medic",     2100, 16, 10, 0, 10, 1, 0, false};
    s.players[25] = {25, "RockAmmo",       "#205", 2, "ammo",      1800, 8,  0,  0, 0,  1, 0, false};

    // Earth Dummy Player
    s.players[102] = {102, "", "", 2, "", 21800, 55, 103, 2, 35, 4, 0, false, 0, 0, 0, 0, 0, true};

    s.player_rankings_by_team[1] = {11, 12, 13, 14, 15};
    s.player_rankings_by_team[2] = {21, 22, 23, 24, 25};

    s.event_scroller = {
        {230000, "<font color=\"#FF5000\">AlphaCommander</font> zaps <font color=\"#A0FF00\">TerraCommander</font>"},
        {235000, "<font color=\"#FF5000\">FireHeavy</font> missiled <font color=\"#A0FF00\">StoneHeavy</font>"},
        {240000, "<font color=\"#FF5000\">AlphaCommander</font> activates nuke"},
        {245000, "<font color=\"#FF5000\">AlphaCommander</font> detonates nuke"}
    };

    return s;
}

GameStateSnapshot MockGameState::CreateMockLaserballState() {
    GameStateSnapshot s = CreateMockSM5State();
    s.game_type = "Laserball";
    s.max_game_length_seconds = 720;
    s.ball_carrier_player_id = 11;
    s.teams[1].score = 4;
    s.teams[2].score = 2;
    return s;
}

}  // namespace live_renderer

