#include <gtest/gtest.h>

#include <chrono>
#include <future>
#include <thread>
#include <vector>

#include "live_renderer/lfstats/competition_info.hpp"
#include "live_renderer/lfstats/lfstats_fetcher.hpp"

namespace live_renderer {
namespace {

TEST(CompetitionInfoTest, ConstructorAndAccessors) {
    CompetitionInfo comp;
    EXPECT_TRUE(comp.GetName().empty());
    EXPECT_TRUE(comp.GetSlug().empty());

    comp.SetName("Syracuse Trios 2026");
    comp.SetSlug("syracuse_trios_2026");
    EXPECT_EQ(comp.GetName(), "Syracuse Trios 2026");
    EXPECT_EQ(comp.GetSlug(), "syracuse_trios_2026");

    CompetitionInfo comp2("Syracuse Trios 2026", "syracuse_trios_2026");
    EXPECT_EQ(comp, comp2);

    CompetitionInfo comp3("Other", "other");
    EXPECT_NE(comp, comp3);
}

TEST(LFStatsFetcherTest, DefaultOptionsAndSetters) {
    LFStatsFetcher fetcher;
    EXPECT_FALSE(fetcher.IsTestMode());
    EXPECT_EQ(fetcher.GetTestDataDir(), "tests/fixtures/lfstats");
    EXPECT_EQ(fetcher.GetBaseUrl(), "https://lfstats.com/api");
    EXPECT_EQ(fetcher.GetTimeoutMs(), 10000);
    EXPECT_EQ(fetcher.GetUserAgent(), "lfdata/1.0");

    fetcher.SetTestMode(true);
    fetcher.SetTestDataDir("custom/fixtures");
    fetcher.SetBaseUrl("https://example.com/api");
    fetcher.SetTimeoutMs(5000);
    fetcher.SetUserAgent("custom/2.0");

    EXPECT_TRUE(fetcher.IsTestMode());
    EXPECT_EQ(fetcher.GetTestDataDir(), "custom/fixtures");
    EXPECT_EQ(fetcher.GetBaseUrl(), "https://example.com/api");
    EXPECT_EQ(fetcher.GetTimeoutMs(), 5000);
    EXPECT_EQ(fetcher.GetUserAgent(), "custom/2.0");
}

TEST(LFStatsFetcherTest, DefaultTestDataPathsAndResolver) {
    const auto& default_paths = LFStatsFetcher::GetDefaultTestDataPaths();
    EXPECT_FALSE(default_paths.empty());

    // Resolve without preferred path should find an existing default path with competitions
    std::string resolved = LFStatsFetcher::ResolveDefaultTestDataDir();
    EXPECT_FALSE(resolved.empty());

    // Preferred path that exists is preserved
    std::string custom_resolved = LFStatsFetcher::ResolveDefaultTestDataDir("tests/fixtures/lfstats");
    EXPECT_EQ(custom_resolved, "tests/fixtures/lfstats");
}

TEST(LFStatsFetcherTest, FetchCompetitionsTestMode) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    auto competitions = fetcher.FetchCompetitions();

    ASSERT_EQ(competitions.size(), 68u);
    EXPECT_EQ(competitions[0].GetSlug(), "syracuse_trios_2026");
    EXPECT_EQ(competitions[0].GetName(), "Syracuse Trios 2026");
    EXPECT_EQ(competitions[3].GetSlug(), "internationals_2026");
    EXPECT_EQ(competitions[3].GetName(), "Internationals 2026");

    auto alias = fetcher.FetchAllCompetitions();
    EXPECT_EQ(competitions, alias);
}

TEST(LFStatsFetcherTest, FetchCompetitionScheduleTestMode) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    auto schedule = fetcher.FetchCompetitionSchedule("syracuse_trios_2026");

    ASSERT_EQ(schedule.size(), 5u);

    const auto& g1 = schedule[0];
    EXPECT_EQ(g1.GetGameName(), "R1 M1 G1");
    ASSERT_TRUE(g1.GetRoundNumber().has_value());
    EXPECT_EQ(*g1.GetRoundNumber(), 1);
    ASSERT_TRUE(g1.GetMatchNumber().has_value());
    EXPECT_EQ(*g1.GetMatchNumber(), 1);
    ASSERT_TRUE(g1.GetGameNumber().has_value());
    EXPECT_EQ(*g1.GetGameNumber(), 1);
    EXPECT_EQ(g1.GetStageIndicator(), "G");

    ASSERT_EQ(g1.GetTeamNames().size(), 2u);
    EXPECT_EQ(g1.GetTeamNames()[0],
              "Baden's Overly Optimistic Buddies & Fireball Friends");
    EXPECT_EQ(g1.GetTeamNames()[1],
              "Death By Budder Knife & Still Expendable");

    ASSERT_TRUE(g1.GetTeamScores().has_value());
    ASSERT_EQ(g1.GetTeamScores()->size(), 2u);
    EXPECT_EQ((*g1.GetTeamScores())[0], 41172);
    EXPECT_EQ((*g1.GetTeamScores())[1], 11229);
    EXPECT_TRUE(g1.IsComplete());

    ASSERT_TRUE(g1.GetScoreDifferential().has_value());
    EXPECT_EQ(*g1.GetScoreDifferential(), 29943);

    ASSERT_TRUE(g1.GetActualStartTimeMs().has_value());
    EXPECT_GT(*g1.GetActualStartTimeMs(), 0LL);

    auto alias = fetcher.FetchSchedule("syracuse_trios_2026");
    EXPECT_EQ(schedule, alias);

    auto tournament_alias =
        fetcher.FetchTournamentSchedule("syracuse_trios_2026");
    EXPECT_EQ(schedule, tournament_alias);
}

TEST(LFStatsFetcherTest, FetchCompetitionScheduleInternationals2026TestMode) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    auto schedule = fetcher.FetchCompetitionSchedule("internationals_2026");

    ASSERT_EQ(schedule.size(), 5u);

    // Games 1-3 have scores and are complete
    EXPECT_EQ(schedule[0].GetGameName(), "R1 M1 G1");
    ASSERT_TRUE(schedule[0].GetTeamScores().has_value());
    EXPECT_EQ((*schedule[0].GetTeamScores())[0], 44452);
    EXPECT_EQ((*schedule[0].GetTeamScores())[1], 28130);
    EXPECT_TRUE(schedule[0].IsComplete());

    EXPECT_EQ(schedule[1].GetGameName(), "R1 M2 G1");
    EXPECT_TRUE(schedule[1].IsComplete());

    EXPECT_EQ(schedule[2].GetGameName(), "R1 M3 G1");
    EXPECT_TRUE(schedule[2].IsComplete());

    // Games 4-5 have no results yet
    const auto& g4 = schedule[3];
    EXPECT_EQ(g4.GetGameName(), "R1 M4 G1");
    EXPECT_FALSE(g4.GetTeamScores().has_value());
    EXPECT_FALSE(g4.GetScoreDifferential().has_value());
    EXPECT_FALSE(g4.GetActualStartTimeMs().has_value());
    EXPECT_FALSE(g4.IsComplete());

    const auto& g5 = schedule[4];
    EXPECT_EQ(g5.GetGameName(), "R1 M1 G2");
    EXPECT_FALSE(g5.GetTeamScores().has_value());
    EXPECT_FALSE(g5.GetScoreDifferential().has_value());
    EXPECT_FALSE(g5.GetActualStartTimeMs().has_value());
    EXPECT_FALSE(g5.IsComplete());
}

TEST(LFStatsFetcherTest, FetchFromTestCompetitionsDataset) {
    LFStatsFetcher fetcher(true, "tests/fixtures/test_competitions");

    auto comps = fetcher.FetchCompetitions();
    ASSERT_EQ(comps.size(), 2u);
    EXPECT_EQ(comps[0].GetSlug(), "internationals_2026");
    EXPECT_EQ(comps[1].GetSlug(), "syracuse_trios_2026");

    auto intl_sched = fetcher.FetchCompetitionSchedule("internationals_2026");
    ASSERT_EQ(intl_sched.size(), 5u);
    EXPECT_FALSE(intl_sched[3].IsComplete());
    EXPECT_FALSE(intl_sched[4].IsComplete());

    auto syr_sched = fetcher.FetchCompetitionSchedule("syracuse_trios_2026");
    ASSERT_EQ(syr_sched.size(), 5u);
    for (const auto& g : syr_sched) {
        EXPECT_TRUE(g.IsComplete());
        EXPECT_TRUE(g.GetTeamScores().has_value());
    }
}

TEST(LFStatsFetcherTest, InvalidCompetitionSlugThrows) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    EXPECT_THROW(fetcher.FetchCompetitionSchedule(""), std::invalid_argument);
    EXPECT_THROW(
        fetcher.FetchCompetitionSchedule("   "), std::invalid_argument);
    EXPECT_THROW(
        fetcher.FetchCompetitionSchedule("non_existent_competition"),
        std::runtime_error);
}

TEST(LFStatsFetcherTest, CustomHttpTransportMocking) {
    LFStatsFetcher fetcher(false);
    fetcher.SetBaseUrl("https://mockapi.local");

    fetcher.SetHttpTransport([](
        const std::string& url,
        const std::string& user_agent,
        int64_t timeout_ms) -> std::string {
        (void)user_agent;
        (void)timeout_ms;
        if (url == "https://mockapi.local/competitions") {
            return R"({"data":[{"name":"Winter Cup","slug":"winter_cup"}]})";
        }
        if (url == "https://mockapi.local/competitions/winter_cup/schedule") {
            return R"([{"gameName":"R1 M1 G1",)"
                   R"("scheduledStartTime":"2026-12-01T10:00:00.000Z",)"
                   R"("team1Name":"Alpha","team2Name":"Beta",)"
                   R"("team1Score":15000,"team2Score":12000}])";
        }
        throw std::runtime_error("Not found");
    });

    auto competitions = fetcher.FetchCompetitions();
    ASSERT_EQ(competitions.size(), 1u);
    EXPECT_EQ(competitions[0].GetName(), "Winter Cup");
    EXPECT_EQ(competitions[0].GetSlug(), "winter_cup");

    auto schedule = fetcher.FetchCompetitionSchedule("winter_cup");
    ASSERT_EQ(schedule.size(), 1u);
    EXPECT_EQ(schedule[0].GetGameName(), "R1 M1 G1");
    EXPECT_EQ(schedule[0].GetTeamNames()[0], "Alpha");
    EXPECT_EQ(schedule[0].GetTeamNames()[1], "Beta");
    ASSERT_TRUE(schedule[0].GetScoreDifferential().has_value());
    EXPECT_EQ(*schedule[0].GetScoreDifferential(), 3000);
}

TEST(LFStatsFetcherTest, AsyncFuturesNonBlocking) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    auto fut_comps = fetcher.FetchCompetitionsAsync();
    auto fut_sched = fetcher.FetchCompetitionScheduleAsync(
        "syracuse_trios_2026");

    ASSERT_TRUE(fut_comps.valid());
    ASSERT_TRUE(fut_sched.valid());

    auto comps = fut_comps.get();
    EXPECT_EQ(comps.size(), 68u);

    auto sched = fut_sched.get();
    EXPECT_EQ(sched.size(), 5u);
}

TEST(LFStatsFetcherTest, AsyncCallbacksNonBlocking) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    std::promise<std::vector<CompetitionInfo>> promise_comps;
    auto future_comps = promise_comps.get_future();
    fetcher.FetchCompetitionsAsync(
        [&promise_comps](
            const std::vector<CompetitionInfo>& result,
            const std::string& error) {
            EXPECT_TRUE(error.empty());
            promise_comps.set_value(result);
        });

    std::promise<std::vector<ScheduledGame>> promise_sched;
    auto future_sched = promise_sched.get_future();
    fetcher.FetchCompetitionScheduleAsync(
        "syracuse_trios_2026",
        [&promise_sched](
            const std::vector<ScheduledGame>& result,
            const std::string& error) {
            EXPECT_TRUE(error.empty());
            promise_sched.set_value(result);
        });

    auto comps = future_comps.get();
    EXPECT_EQ(comps.size(), 68u);

    auto sched = future_sched.get();
    EXPECT_EQ(sched.size(), 5u);
}

TEST(LFStatsFetcherTest, ConcurrentMultipleRequests) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    constexpr int kNumRequests = 16;
    std::vector<std::future<std::vector<ScheduledGame>>> futures;
    futures.reserve(kNumRequests);

    for (int i = 0; i < kNumRequests; ++i) {
        futures.push_back(
            fetcher.FetchCompetitionScheduleAsync("syracuse_trios_2026"));
    }

    for (auto& fut : futures) {
        auto result = fut.get();
        EXPECT_EQ(result.size(), 5u);
    }
}

TEST(LFStatsFetcherTest, ApiKeyConfiguration) {
    LFStatsFetcher fetcher;
    EXPECT_TRUE(fetcher.GetApiKey().empty());

    fetcher.SetApiKey("my_test_api_key_456");
    EXPECT_EQ(fetcher.GetApiKey(), "my_test_api_key_456");
}

TEST(LFStatsFetcherTest, HttpTransportWithKeyReceivesApiKey) {
    LFStatsFetcher fetcher;
    fetcher.SetTestMode(false);
    fetcher.SetApiKey("secret_token_xyz");

    std::string captured_url;
    std::string captured_ua;
    std::string captured_key;
    int64_t captured_timeout = 0;

    fetcher.SetHttpTransport(
        [&](const std::string& url,
            const std::string& user_agent,
            const std::string& api_key,
            int64_t timeout_ms) -> std::string {
            captured_url = url;
            captured_ua = user_agent;
            captured_key = api_key;
            captured_timeout = timeout_ms;
            return "[]";
        });

    auto comps = fetcher.FetchCompetitions();
    EXPECT_TRUE(comps.empty());
    EXPECT_EQ(captured_url, "https://lfstats.com/api/competitions");
    EXPECT_EQ(captured_ua, "lfdata/1.0");
    EXPECT_EQ(captured_key, "secret_token_xyz");
    EXPECT_EQ(captured_timeout, 10000);
}

TEST(LFStatsFetcherTest, FetchCompetitionTeamsTestMode) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    auto teams = fetcher.FetchCompetitionTeams("syracuse_trios_2026");

    ASSERT_EQ(teams.size(), 4u);
    EXPECT_EQ(teams[0].GetName(), "Baden's Overly Optimistic Buddies");
    EXPECT_EQ(teams[0].GetSlug(), "baden_s_overly_optimistic_buddies");
    EXPECT_EQ(teams[0].GetLogoUrl(), "https://example.com/logos/boob.png");
    ASSERT_EQ(teams[0].GetPlayers().size(), 3u);
    EXPECT_EQ(teams[0].GetPlayers()[0], "Baden");
    EXPECT_EQ(teams[0].GetPlayers()[1], "Sunny");
    EXPECT_EQ(teams[0].GetPlayers()[2], "Cheer");

    EXPECT_EQ(teams[2].GetName(), "Death By Budder Knife");
    EXPECT_FALSE(teams[2].GetLogoUrl().empty());
    EXPECT_EQ(teams[2].GetPlayers().size(), 3u);

    auto alias = fetcher.FetchTeams("syracuse_trios_2026");
    EXPECT_EQ(teams.size(), alias.size());
}

TEST(LFStatsFetcherTest, FetchCompetitionTeamsEmptySlugThrows) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    EXPECT_THROW(fetcher.FetchCompetitionTeams(""), std::invalid_argument);
    EXPECT_THROW(fetcher.FetchCompetitionTeams("   "), std::invalid_argument);
}

TEST(LFStatsFetcherTest, FetchCompetitionTeamsAsyncFuturesAndCallbacks) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    auto future = fetcher.FetchCompetitionTeamsAsync("syracuse_trios_2026");
    auto teams = future.get();
    EXPECT_EQ(teams.size(), 4u);

    std::promise<std::vector<CompetitionTeam>> promise;
    auto cb_future = promise.get_future();
    fetcher.FetchCompetitionTeamsAsync(
        "syracuse_trios_2026",
        [&promise](
            const std::vector<CompetitionTeam>& result,
            const std::string& error) {
            EXPECT_TRUE(error.empty());
            promise.set_value(result);
        });

    auto cb_teams = cb_future.get();
    EXPECT_EQ(cb_teams.size(), 4u);
}

TEST(LFStatsFetcherTest, FetchCompetitionPlayerDetailsTestMode) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
    auto players = fetcher.FetchCompetitionPlayerDetails("syracuse_trios_2026");

    ASSERT_EQ(players.size(), 12u);
    EXPECT_EQ(players[0].entity_id, "4-1-101");
    EXPECT_EQ(players[0].player_name, "Baden");
    EXPECT_EQ(players[0].picture_url, "https://example.com/players/baden.png");
    EXPECT_EQ(players[0].team_name, "Baden's Overly Optimistic Buddies");
    EXPECT_EQ(players[0].team_logo_url, "https://example.com/logos/boob.png");

    EXPECT_EQ(players[1].entity_id, "4-1-102");
    EXPECT_EQ(players[1].player_name, "Sunny");
    EXPECT_TRUE(players[1].picture_url.empty());
}

TEST(LFStatsFetcherTest, FetchCompetitionPlayerDetailsAsyncFuturesAndCallbacks) {
    LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");

    auto future = fetcher.FetchCompetitionPlayerDetailsAsync("syracuse_trios_2026");
    auto players = future.get();
    EXPECT_EQ(players.size(), 12u);

    std::promise<std::vector<CompetitionPlayerInfo>> promise;
    auto cb_future = promise.get_future();
    fetcher.FetchCompetitionPlayerDetailsAsync(
        "syracuse_trios_2026",
        [&promise](
            const std::vector<CompetitionPlayerInfo>& result,
            const std::string& error) {
            EXPECT_TRUE(error.empty());
            promise.set_value(result);
        });

    auto cb_players = cb_future.get();
    EXPECT_EQ(cb_players.size(), 12u);
}

}  // namespace
}  // namespace live_renderer

