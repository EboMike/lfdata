#include <gtest/gtest.h>
#include "live_renderer/components/game_timer_element.hpp"
#include "live_renderer/components/scorecard_helper.hpp"
#include "live_renderer/state/mock_game_state.hpp"

using namespace live_renderer;

TEST(GameTimerTest, FormatsCountdownAccurately) {
    GameStateSnapshot state;
    state.in_session = true;
    state.max_game_length_seconds = 900; // 15:00
    state.game_start_time_local_ms = 100000;

    // 2 minutes in (120,000 ms elapsed) -> 13:00 remaining
    std::string t1 = GameTimerElement::FormatRemainingTime(state, 220000);
    EXPECT_EQ(t1, "13:00");

    // 14m 30s in -> 00:30 remaining
    std::string t2 = GameTimerElement::FormatRemainingTime(state, 100000 + 870000);
    EXPECT_EQ(t2, "00:30");

    // Past 15m -> 00:00
    std::string t3 = GameTimerElement::FormatRemainingTime(state, 100000 + 950000);
    EXPECT_EQ(t3, "00:00");
}

TEST(GameTimerTest, FreezesWhenGameOver) {
    GameStateSnapshot state;
    state.in_session = true;
    state.game_over = true;
    state.max_game_length_seconds = 900;
    state.game_start_time_local_ms = 100000;
    state.latest_event_time_ms = 600000; // Game ended at 10:00 (5:00 remaining)

    std::string t = GameTimerElement::FormatRemainingTime(state, 99999999);
    EXPECT_EQ(t, "05:00");
}

TEST(GameTimerTest, FormatsCountdownWithEventTime) {
    GameStateSnapshot state;
    state.in_session = true;
    state.max_game_length_seconds = 900;
    state.game_start_time_local_ms = 0;
    state.latest_event_time_ms = 300000; // 5m in -> 10:00 remaining

    std::string t = GameTimerElement::FormatRemainingTime(state, 0);
    EXPECT_EQ(t, "10:00");
}

TEST(ScorecardHelperTest, SortsTeamsAndPlayers) {
    auto state = MockGameState::CreateMockSM5State();

    // Check team sorting
    auto teams_ranked = ScorecardHelper::GetSortedTeamIds(state, TeamSortOrder::Ranking);
    ASSERT_EQ(teams_ranked.size(), 2);
    EXPECT_EQ(teams_ranked[0], 1);
    EXPECT_EQ(teams_ranked[1], 2);

    // Check Fire players sorted by ranking with totals
    auto fire_ranked = ScorecardHelper::GetSortedPlayerIds(state, 1, PlayerSortOrder::Ranking, true);
    ASSERT_EQ(fire_ranked.size(), 6); // 5 players + 1 dummy
    EXPECT_EQ(fire_ranked[0], 11);
    EXPECT_EQ(fire_ranked[4], 15);
    EXPECT_EQ(fire_ranked[5], 101); // dummy player at the end

    // Check Fire players sorted by index
    auto fire_by_id = ScorecardHelper::GetSortedPlayerIds(
        state, 1, PlayerSortOrder::Index, false);
    ASSERT_EQ(fire_by_id.size(), 5);
    EXPECT_EQ(fire_by_id, (std::vector<int>{11, 12, 13, 14, 15}));

    // Add Neutral team with 0 players and a dummy totals player
    TeamSnapshot t3;
    t3.id = 3;
    t3.name = "Neutral";
    t3.rgb = "#808080";
    t3.dummy_player_id = 103;
    t3.player_ids = {};
    state.teams[3] = t3;

    PlayerSnapshot d3;
    d3.id = 103;
    d3.team_id = 3;
    d3.is_dummy = true;
    state.players[103] = d3;

    // Neutral team must NOT be in sorted teams since it has no players
    auto teams_ranked_with_neutral = ScorecardHelper::GetSortedTeamIds(
        state, TeamSortOrder::Ranking);
    ASSERT_EQ(teams_ranked_with_neutral.size(), 2);
    EXPECT_EQ(teams_ranked_with_neutral[0], 1);
    EXPECT_EQ(teams_ranked_with_neutral[1], 2);

    auto teams_index_with_neutral = ScorecardHelper::GetSortedTeamIds(
        state, TeamSortOrder::Index);
    ASSERT_EQ(teams_index_with_neutral.size(), 2);

    // Neutral team scorecard must return NO player rows and NO totals row
    auto neutral_players = ScorecardHelper::GetSortedPlayerIds(
        state, 3, PlayerSortOrder::Ranking, true);
    EXPECT_TRUE(neutral_players.empty());

    // If dummy player is already in player_ids, it must not be duplicated
    state.teams[1].player_ids.push_back(101);
    auto fire_no_dup = ScorecardHelper::GetSortedPlayerIds(
        state, 1, PlayerSortOrder::Ranking, true);
    EXPECT_EQ(fire_no_dup.size(), 6);
    EXPECT_EQ(fire_no_dup.back(), 101);
}

TEST(ScorecardHelperTest, RowColorStyling) {
    auto state = MockGameState::CreateMockSM5State();
    std::string fire_rgb = "#FF5000";

    // Alpha is active (state 0, lives > 0) -> #FF5000
    EXPECT_EQ(ScorecardHelper::GetRowTextColor(state.players[11], fire_rgb), fire_rgb);

    // Blaze is down (state 3) -> darker tone of #FF5000 (#7f2800)
    EXPECT_EQ(ScorecardHelper::GetRowTextColor(state.players[13], fire_rgb), "#7f2800");

    // Pyro is dead (state 4, lives 0) -> #808080 (gray)
    EXPECT_EQ(ScorecardHelper::GetRowTextColor(state.players[15], fire_rgb), "#808080");

    // Dummy player -> team color
    EXPECT_EQ(ScorecardHelper::GetRowTextColor(state.players[101], fire_rgb), fire_rgb);
}

