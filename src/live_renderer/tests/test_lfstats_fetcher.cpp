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

    ASSERT_EQ(schedule.size(), 54u);

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

    auto alias = fetcher.FetchSchedule("syracuse_trios_2026");
    EXPECT_EQ(schedule, alias);
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
    EXPECT_EQ(sched.size(), 54u);
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
    EXPECT_EQ(sched.size(), 54u);
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
        EXPECT_EQ(result.size(), 54u);
    }
}

}  // namespace
}  // namespace live_renderer

