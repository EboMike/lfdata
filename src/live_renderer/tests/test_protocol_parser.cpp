#include <gtest/gtest.h>
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/state/live_state_store.hpp"

using namespace live_renderer;

TEST(ProtocolParserTest, ParsesCenterAndGameType) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("28\t100\t4-43\tLoveland\r\n"));
    EXPECT_TRUE(parser.ParseLine("17\t100\tSM5\t900\r\n"));

    auto s = store.GetSnapshot();
    EXPECT_EQ(s.center_id, "4-43");
    EXPECT_EQ(s.center_name, "Loveland");
    EXPECT_EQ(s.game_type, "SM5");
    EXPECT_EQ(s.max_game_length_seconds, 900);
}

TEST(ProtocolParserTest, ParsesTeamAndDummyPlayer) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("15\t50\t1\tFire\t#FF5000\t101\r\n"));
    EXPECT_TRUE(parser.ParseLine("1\t200\t1\t1200\r\n"));

    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.teams.contains(1));
    EXPECT_EQ(s.teams[1].name, "Fire");
    EXPECT_EQ(s.teams[1].rgb, "#FF5000");
    EXPECT_EQ(s.teams[1].dummy_player_id, 101);
    EXPECT_EQ(s.teams[1].score, 1200);

    ASSERT_TRUE(s.players.contains(101));
    EXPECT_TRUE(s.players[101].is_dummy);
}

TEST(ProtocolParserTest, ParsesPlayerStatsAndState) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("16\t100\t11\tAlpha\t#101\t1\tcommander\r\n"));
    EXPECT_TRUE(parser.ParseLine("3\t150\t11\t5400\r\n"));
    EXPECT_TRUE(parser.ParseLine("4\t150\t11\t12\r\n"));
    EXPECT_TRUE(parser.ParseLine("5\t150\t11\t25\r\n"));
    EXPECT_TRUE(parser.ParseLine("6\t150\t11\t20\r\n"));
    EXPECT_TRUE(parser.ParseLine("7\t150\t11\t3\r\n"));
    EXPECT_TRUE(parser.ParseLine("9\t160\t11\t3\r\n")); // Down
    EXPECT_TRUE(parser.ParseLine("10\t160\t11\t4\r\n")); // Missiles
    EXPECT_TRUE(parser.ParseLine("23\t170\t11\t1\r\n")); // Rapid fire

    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.players.contains(11));
    const auto& p = s.players[11];
    EXPECT_EQ(p.name, "Alpha");
    EXPECT_EQ(p.role, "commander");
    EXPECT_EQ(p.score, 5400);
    EXPECT_EQ(p.lives, 12);
    EXPECT_EQ(p.shots, 25);
    EXPECT_EQ(p.special_points, 20);
    EXPECT_EQ(p.hitpoints, 3);
    EXPECT_EQ(p.state, 3);
    EXPECT_EQ(p.missiles, 4);
    EXPECT_TRUE(p.has_rapid_fire);
}

TEST(ProtocolParserTest, ParsesRankingsAndEvents) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("26\t500\t1\t11,12,13\r\n"));
    EXPECT_TRUE(parser.ParseLine("27\t500\t1,2\r\n"));
    EXPECT_TRUE(parser.ParseLine("8\t600\t<font color=\"#FF5000\">Alpha</font> zapped Bravo\r\n"));
    EXPECT_TRUE(parser.ParseLine("25\t610\t1\tAlpha detonates nuke\r\n"));

    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.player_rankings_by_team.contains(1));
    EXPECT_EQ(s.player_rankings_by_team[1], (std::vector<int>{11, 12, 13}));
    EXPECT_EQ(s.team_rankings, (std::vector<int>{1, 2}));
    ASSERT_EQ(s.event_scroller.size(), 1);
    EXPECT_EQ(s.event_scroller[0].formatted_message, "<font color=\"#FF5000\">Alpha</font> zapped Bravo");
    ASSERT_EQ(s.important_events.size(), 1);
    EXPECT_EQ(s.important_events[0].id, 1);
    EXPECT_EQ(s.important_events[0].timestamp_ms, 610);
    EXPECT_EQ(s.important_events[0].formatted_message, "Alpha detonates nuke");
}

TEST(ProtocolParserTest, ParsesImportantEventsWithReplacementAndRejection) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("25\t600\t10\tCommander activates nuke\r\n"));
    EXPECT_TRUE(parser.ParseLine("25\t610\t11\tMedic has been eliminated\r\n"));

    auto s = store.GetSnapshot();
    ASSERT_EQ(s.important_events.size(), 2);
    EXPECT_EQ(s.important_events[0].id, 10);
    EXPECT_EQ(
        s.important_events[0].formatted_message,
        "Commander activates nuke"
    );
    EXPECT_EQ(s.important_events[1].id, 11);
    EXPECT_EQ(
        s.important_events[1].formatted_message,
        "Medic has been eliminated"
    );

    // Replacement of ID 10
    EXPECT_TRUE(parser.ParseLine("25\t620\t10\tCommander detonates nuke\r\n"));
    s = store.GetSnapshot();
    ASSERT_EQ(s.important_events.size(), 2);
    EXPECT_EQ(s.important_events[0].id, 10);
    EXPECT_EQ(s.important_events[0].timestamp_ms, 620);
    EXPECT_EQ(
        s.important_events[0].formatted_message,
        "Commander detonates nuke"
    );

    // Malformed lines with missing fields rejected
    EXPECT_FALSE(parser.ParseLine("25\t630\r\n"));
    EXPECT_FALSE(parser.ParseLine("25\t630\t12\r\n"));
}

TEST(ProtocolParserTest, HandlesResetAndGameOver) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("16\t100\t11\tAlpha\t#101\t1\tcommander\r\n"));
    EXPECT_TRUE(parser.ParseLine("99\t900000\r\n"));
    EXPECT_TRUE(store.GetSnapshot().game_over);

    EXPECT_TRUE(parser.ParseLine("98\t0\r\n")); // Reset
    auto s = store.GetSnapshot();
    EXPECT_FALSE(s.game_over);
    EXPECT_TRUE(s.in_session);
    EXPECT_TRUE(s.players.empty());
}

