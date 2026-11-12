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

TEST(ProtocolParserTest, ParsesNewStatsAndDataTypes) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(
        parser.ParseLine("16\t100\t11\tAlpha\t#101\t1\tcommander\r\n"));
    EXPECT_TRUE(
        parser.ParseLine("5\t150\t11\t25\t100\t54\t54.0%\r\n"));
    EXPECT_TRUE(
        parser.ParseLine("10\t160\t11\t4\t5\t3\r\n"));
    EXPECT_TRUE(
        parser.ParseLine("29\t170\t11\t2\r\n"));
    EXPECT_TRUE(
        parser.ParseLine("30\t180\t11\t1\r\n"));
    EXPECT_TRUE(
        parser.ParseLine("31\t190\t11\t1/3/-1\r\n"));

    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.players.contains(11));
    const auto& p = s.players[11];
    EXPECT_EQ(p.shots, 25);
    EXPECT_EQ(p.shots_fired, 100);
    EXPECT_EQ(p.shots_hit, 54);
    EXPECT_EQ(p.accuracy, "54.0%");
    EXPECT_EQ(p.missiles, 4);
    EXPECT_EQ(p.missiles_fired, 5);
    EXPECT_EQ(p.missiles_landed, 3);
    EXPECT_EQ(p.nukes_activated, 2);
    EXPECT_EQ(p.nukes_detonated, 1);
    EXPECT_EQ(p.medic_hits, "1/3/-1");
}

TEST(ProtocolParserTest, PlayerProfilePictureDefaultAndFallback) {
    LiveStateStore store;
    ProtocolParser parser(store);

    EXPECT_TRUE(parser.ParseLine("16\t100\t11\tBaden\t#4-1-101\t1\tcommander\r\n"));
    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.players.contains(11));
    EXPECT_EQ(
        s.players[11].picture_url,
        "https://lfstats-modern-images.s3.us-west-1.amazonaws.com/8c3b3ffc-85f7-49aa-a6a0-78ce8b0f658f");

    store.SetDefaultProfilePictureUrl("https://example.com/custom_fallback.png");
    EXPECT_EQ(store.GetDefaultProfilePictureUrl(), "https://example.com/custom_fallback.png");
    s = store.GetSnapshot();
    EXPECT_EQ(s.players[11].picture_url, "https://example.com/custom_fallback.png");
}

TEST(ProtocolParserTest, PlayerProfilePictureFromCompetitionDetails) {
    LiveStateStore store;
    ProtocolParser parser(store);

    std::vector<PlayerDetailsUpdate> details = {
        {
            "4-1-101",
            "Baden",
            "https://example.com/players/baden.png",
            "Baden's Buddies",
            "https://example.com/logos/buddies.png"
        },
        {
            "4-1-102",
            "Sunny",
            "",  // empty picture URL -> should fallback to default
            "Baden's Buddies",
            "https://example.com/logos/buddies.png"
        }
    };
    store.UpdateCompetitionPlayerDetails(details);

    // Player 11 entity ID is "#4-1-101" (with hash)
    EXPECT_TRUE(parser.ParseLine("16\t100\t11\tBaden\t#4-1-101\t1\tcommander\r\n"));
    // Player 12 entity ID is "4-1-102" (without hash)
    EXPECT_TRUE(parser.ParseLine("16\t100\t12\tSunny\t4-1-102\t1\theavy\r\n"));

    auto s = store.GetSnapshot();
    ASSERT_TRUE(s.players.contains(11));
    EXPECT_EQ(s.players[11].picture_url, "https://example.com/players/baden.png");
    EXPECT_EQ(s.players[11].team_name, "Baden's Buddies");
    EXPECT_EQ(s.players[11].team_logo_url, "https://example.com/logos/buddies.png");

    ASSERT_TRUE(s.players.contains(12));
    EXPECT_EQ(s.players[12].picture_url, store.GetDefaultProfilePictureUrl());
    EXPECT_EQ(s.players[12].team_name, "Baden's Buddies");
}

