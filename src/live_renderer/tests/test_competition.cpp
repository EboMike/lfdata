#include <gtest/gtest.h>

#include "live_renderer/model/competition.hpp"
#include "live_renderer/model/competition_team.hpp"
#include "live_renderer/model/scheduled_game.hpp"

namespace live_renderer {
namespace {

TEST(CompetitionTeamTest, DefaultConstructorInitializesEmpty) {
    CompetitionTeam team;
    EXPECT_TRUE(team.GetSlug().empty());
    EXPECT_TRUE(team.GetName().empty());
    EXPECT_TRUE(team.GetShortName().empty());
    EXPECT_TRUE(team.GetLogoUrl().empty());
    EXPECT_TRUE(team.GetPlayers().empty());
}

TEST(CompetitionTeamTest, ParameterizedConstructorAndGetters) {
    std::vector<std::string> players = {"Alpha", "Bravo", "Charlie"};
    CompetitionTeam team(
        "tigers", "Thunder Tigers", "TIG",
        "https://example.com/tigers.png", players);

    EXPECT_EQ(team.GetSlug(), "tigers");
    EXPECT_EQ(team.GetName(), "Thunder Tigers");
    EXPECT_EQ(team.GetShortName(), "TIG");
    EXPECT_EQ(team.GetLogoUrl(), "https://example.com/tigers.png");
    EXPECT_EQ(team.GetPlayers(), players);
}

TEST(CompetitionTeamTest, SettersAndRosterManagement) {
    CompetitionTeam team;
    team.SetSlug("lions");
    team.SetName("Mighty Lions");
    team.SetShortName("LIO");
    team.SetLogoUrl("https://example.com/lions.png");

    EXPECT_EQ(team.GetSlug(), "lions");
    EXPECT_EQ(team.GetName(), "Mighty Lions");
    EXPECT_EQ(team.GetShortName(), "LIO");
    EXPECT_EQ(team.GetLogoUrl(), "https://example.com/lions.png");

    EXPECT_FALSE(team.HasPlayer("Hunter"));
    team.AddPlayer("Hunter");
    team.AddPlayer("Sniper");
    EXPECT_TRUE(team.HasPlayer("Hunter"));
    EXPECT_TRUE(team.HasPlayer("Sniper"));
    EXPECT_EQ(team.GetPlayers().size(), 2u);

    EXPECT_TRUE(team.RemovePlayer("Hunter"));
    EXPECT_FALSE(team.HasPlayer("Hunter"));
    EXPECT_FALSE(team.RemovePlayer("NonExistent"));
    EXPECT_EQ(team.GetPlayers().size(), 1u);

    team.SetPlayers({"Striker", "Defender"});
    EXPECT_EQ(team.GetPlayers().size(), 2u);
    EXPECT_TRUE(team.HasPlayer("Striker"));
    EXPECT_TRUE(team.HasPlayer("Defender"));
}

TEST(CompetitionTeamTest, EqualityOperators) {
    CompetitionTeam team1("slug1", "Team 1", "T1");
    CompetitionTeam team2("slug1", "Team 1", "T1");
    CompetitionTeam team3("slug2", "Team 2", "T2");

    EXPECT_EQ(team1, team2);
    EXPECT_NE(team1, team3);
}

TEST(ScheduledGameTest, DefaultConstructorInitializesDefaults) {
    ScheduledGame game;
    EXPECT_TRUE(game.GetGameName().empty());
    EXPECT_TRUE(game.GetTeamNames().empty());
    EXPECT_TRUE(game.GetTeamLogos().empty());
    EXPECT_FALSE(game.GetScheduledStartTimeMs().has_value());
    EXPECT_FALSE(game.GetScheduledEndTimeMs().has_value());
    EXPECT_FALSE(game.GetRoundNumber().has_value());
    EXPECT_FALSE(game.GetMatchNumber().has_value());
    EXPECT_FALSE(game.GetGameNumber().has_value());
    EXPECT_EQ(game.GetStageIndicator(), "G");
    EXPECT_FALSE(game.GetTeamScores().has_value());
    EXPECT_FALSE(game.IsComplete());
    EXPECT_FALSE(game.GetScoreDifferential().has_value());
}

TEST(ScheduledGameTest, ParameterizedConstructorAndGetters) {
    std::vector<std::string> teams = {"Tigers", "Lions"};
    std::vector<std::string> logos = {"tigers.png", "lions.png"};
    std::vector<int> scores = {12000, 9500};

    ScheduledGame game(
        "R1 M3 G2", teams, logos,
        1720612800000LL, 1720614000000LL,
        1, 3, 2, "G", scores);

    EXPECT_EQ(game.GetGameName(), "R1 M3 G2");
    EXPECT_EQ(game.GetTeamNames(), teams);
    EXPECT_EQ(game.GetTeamLogos(), logos);
    ASSERT_TRUE(game.GetScheduledStartTimeMs().has_value());
    EXPECT_EQ(*game.GetScheduledStartTimeMs(), 1720612800000LL);
    ASSERT_TRUE(game.GetScheduledEndTimeMs().has_value());
    EXPECT_EQ(*game.GetScheduledEndTimeMs(), 1720614000000LL);
    ASSERT_TRUE(game.GetRoundNumber().has_value());
    EXPECT_EQ(*game.GetRoundNumber(), 1);
    ASSERT_TRUE(game.GetMatchNumber().has_value());
    EXPECT_EQ(*game.GetMatchNumber(), 3);
    ASSERT_TRUE(game.GetGameNumber().has_value());
    EXPECT_EQ(*game.GetGameNumber(), 2);
    EXPECT_EQ(game.GetStageIndicator(), "G");
    ASSERT_TRUE(game.GetTeamScores().has_value());
    EXPECT_EQ(*game.GetTeamScores(), scores);
    EXPECT_TRUE(game.IsComplete());
    ASSERT_TRUE(game.GetScoreDifferential().has_value());
    EXPECT_EQ(*game.GetScoreDifferential(), 2500);
}

TEST(ScheduledGameTest, SettersAndTeamLists) {
    ScheduledGame game;
    game.SetGameName("R2 M1 H1");
    game.AddTeamName("Team A");
    game.AddTeamName("Team B");
    game.AddTeamLogo("logo_a.png");
    game.AddTeamLogo("logo_b.png");
    game.SetScheduledStartTimeMs(100000LL);
    game.SetScheduledEndTimeMs(200000LL);
    game.SetRoundNumber(2);
    game.SetMatchNumber(1);
    game.SetGameNumber(1);
    game.SetStageIndicator("H");
    game.SetActualStartTimeMs(105000LL);

    EXPECT_EQ(game.GetGameName(), "R2 M1 H1");
    EXPECT_EQ(game.GetTeamNames().size(), 2u);
    EXPECT_EQ(game.GetTeamLogos().size(), 2u);
    EXPECT_EQ(*game.GetScheduledStartTimeMs(), 100000LL);
    EXPECT_EQ(*game.GetScheduledEndTimeMs(), 200000LL);
    EXPECT_EQ(*game.GetActualStartTimeMs(), 105000LL);
    EXPECT_EQ(*game.GetRoundNumber(), 2);
    EXPECT_EQ(*game.GetMatchNumber(), 1);
    EXPECT_EQ(*game.GetGameNumber(), 1);
    EXPECT_EQ(game.GetStageIndicator(), "H");
}

TEST(ScheduledGameTest, ScoreDifferentialCalculations) {
    ScheduledGame game;
    EXPECT_FALSE(game.GetScoreDifferential().has_value());

    // Single score cannot calculate differential
    game.SetTeamScores(std::vector<int>{5000});
    EXPECT_TRUE(game.IsComplete());
    EXPECT_FALSE(game.GetScoreDifferential().has_value());

    // Two scores: higher minus lower absolute difference
    game.SetTeamScores(std::vector<int>{8000, 11000});
    ASSERT_TRUE(game.GetScoreDifferential().has_value());
    EXPECT_EQ(*game.GetScoreDifferential(), 3000);

    // Tied scores
    game.SetTeamScores(std::vector<int>{7500, 7500});
    ASSERT_TRUE(game.GetScoreDifferential().has_value());
    EXPECT_EQ(*game.GetScoreDifferential(), 0);
}

TEST(ScheduledGameTest, FormatGameName) {
    EXPECT_EQ(
        ScheduledGame::FormatGameName(1, 3, 2, "G"),
        "R1 M3 G2");
    EXPECT_EQ(
        ScheduledGame::FormatGameName(2, 3, 1, "H"),
        "R2 M3 H1");
    EXPECT_EQ(
        ScheduledGame::FormatGameName(2, 3, 1, "OT"),
        "R2 M3 OT1");
    EXPECT_EQ(
        ScheduledGame::FormatGameName(std::nullopt, std::nullopt, 5),
        "G5");
}

TEST(ScheduledGameTest, ParseGameName) {
    std::optional<int> round;
    std::optional<int> match;
    std::optional<int> game;
    std::string stage;

    ScheduledGame::ParseGameName("R1 M3 G2", round, match, game, stage);
    ASSERT_TRUE(round.has_value());
    EXPECT_EQ(*round, 1);
    ASSERT_TRUE(match.has_value());
    EXPECT_EQ(*match, 3);
    ASSERT_TRUE(game.has_value());
    EXPECT_EQ(*game, 2);
    EXPECT_EQ(stage, "G");

    ScheduledGame::ParseGameName("R2 M3 H1", round, match, game, stage);
    ASSERT_TRUE(round.has_value());
    EXPECT_EQ(*round, 2);
    ASSERT_TRUE(match.has_value());
    EXPECT_EQ(*match, 3);
    ASSERT_TRUE(game.has_value());
    EXPECT_EQ(*game, 1);
    EXPECT_EQ(stage, "H");

    ScheduledGame::ParseGameName("R2 M3 OT1", round, match, game, stage);
    ASSERT_TRUE(round.has_value());
    EXPECT_EQ(*round, 2);
    ASSERT_TRUE(match.has_value());
    EXPECT_EQ(*match, 3);
    ASSERT_TRUE(game.has_value());
    EXPECT_EQ(*game, 1);
    EXPECT_EQ(stage, "OT");
}

TEST(ScheduledGameTest, EqualityOperators) {
    ScheduledGame g1("R1 M1 G1");
    ScheduledGame g2("R1 M1 G1");
    ScheduledGame g3("R1 M1 G2");

    EXPECT_EQ(g1, g2);
    EXPECT_NE(g1, g3);
}

TEST(CompetitionTest, DefaultConstructorInitializesDefaults) {
    Competition comp;
    EXPECT_TRUE(comp.GetName().empty());
    EXPECT_TRUE(comp.GetSlug().empty());
    EXPECT_TRUE(comp.GetSite().empty());
    EXPECT_FALSE(comp.GetStartTimeMs().has_value());
    EXPECT_FALSE(comp.GetEndTimeMs().has_value());
    EXPECT_TRUE(comp.GetTeams().empty());
    EXPECT_TRUE(comp.GetSchedule().empty());
    EXPECT_EQ(comp.GetTotalGamesCount(), 0u);
    EXPECT_EQ(comp.GetCompletedGamesCount(), 0u);
}

TEST(CompetitionTest, ParameterizedConstructorAndGetters) {
    std::vector<CompetitionTeam> teams = {
        CompetitionTeam("tigers", "Tigers", "TIG"),
        CompetitionTeam("lions", "Lions", "LIO")
    };
    std::vector<ScheduledGame> schedule = {
        ScheduledGame("R1 M1 G1"),
        ScheduledGame("R1 M1 G2")
    };

    Competition comp(
        "LF World Championships 2026",
        "lf_worlds_2026",
        "Brisbane",
        1720600000000LL,
        1721200000000LL,
        teams,
        schedule);

    EXPECT_EQ(comp.GetName(), "LF World Championships 2026");
    EXPECT_EQ(comp.GetSlug(), "lf_worlds_2026");
    EXPECT_EQ(comp.GetSite(), "Brisbane");
    ASSERT_TRUE(comp.GetStartTimeMs().has_value());
    EXPECT_EQ(*comp.GetStartTimeMs(), 1720600000000LL);
    ASSERT_TRUE(comp.GetEndTimeMs().has_value());
    EXPECT_EQ(*comp.GetEndTimeMs(), 1721200000000LL);
    EXPECT_EQ(comp.GetTeams(), teams);
    EXPECT_EQ(comp.GetSchedule(), schedule);
    EXPECT_EQ(comp.GetTotalGamesCount(), 2u);
}

TEST(CompetitionTest, TeamManagement) {
    Competition comp("Syracuse Trios 2026");
    comp.SetSlug("syracuse_trios_2026");
    comp.SetSite("Syracuse");

    EXPECT_FALSE(comp.HasTeam("bears"));
    EXPECT_EQ(comp.FindTeam("bears"), nullptr);

    CompetitionTeam bears("bears", "Black Bears", "BEA");
    comp.AddTeam(bears);

    EXPECT_TRUE(comp.HasTeam("bears"));
    ASSERT_NE(comp.FindTeam("bears"), nullptr);
    EXPECT_EQ(comp.FindTeam("bears")->GetName(), "Black Bears");

    // Mutable find
    CompetitionTeam* mutable_bears = comp.FindTeam("bears");
    ASSERT_NE(mutable_bears, nullptr);
    mutable_bears->AddPlayer("Grizzly");
    EXPECT_TRUE(comp.FindTeam("bears")->HasPlayer("Grizzly"));

    EXPECT_TRUE(comp.RemoveTeam("bears"));
    EXPECT_FALSE(comp.HasTeam("bears"));
    EXPECT_FALSE(comp.RemoveTeam("nonexistent"));
}

TEST(CompetitionTest, ScheduleManagementAndStatistics) {
    Competition comp("Syracuse Trios 2026");

    ScheduledGame g1("R1 M1 G1", {"Tigers", "Lions"});
    ScheduledGame g2("R1 M2 G1", {"Wolves", "Tigers"});
    g2.SetTeamScores(std::vector<int>{8500, 9200});

    comp.AddScheduledGame(g1);
    comp.AddScheduledGame(g2);

    EXPECT_EQ(comp.GetTotalGamesCount(), 2u);
    EXPECT_EQ(comp.GetCompletedGamesCount(), 1u);

    EXPECT_NE(comp.FindScheduledGame("R1 M1 G1"), nullptr);
    EXPECT_NE(comp.FindScheduledGame("R1 M2 G1"), nullptr);
    EXPECT_EQ(comp.FindScheduledGame("R9 M9 G9"), nullptr);

    // Get games for a specific team
    auto tiger_games = comp.GetGamesForTeam("Tigers");
    EXPECT_EQ(tiger_games.size(), 2u);

    auto wolf_games = comp.GetGamesForTeam("Wolves");
    ASSERT_EQ(wolf_games.size(), 1u);
    EXPECT_EQ(wolf_games[0]->GetGameName(), "R1 M2 G1");

    auto unknown_games = comp.GetGamesForTeam("NonExistent");
    EXPECT_TRUE(unknown_games.empty());

    // Mutable find
    ScheduledGame* mutable_g1 = comp.FindScheduledGame("R1 M1 G1");
    ASSERT_NE(mutable_g1, nullptr);
    mutable_g1->SetTeamScores(std::vector<int>{10000, 8000});
    EXPECT_EQ(comp.GetCompletedGamesCount(), 2u);

    // Remove game
    EXPECT_TRUE(comp.RemoveScheduledGame(0));
    EXPECT_EQ(comp.GetTotalGamesCount(), 1u);
    EXPECT_FALSE(comp.RemoveScheduledGame(999));
}

TEST(CompetitionTest, EqualityOperators) {
    Competition c1("Comp A", "comp_a", "Site A");
    Competition c2("Comp A", "comp_a", "Site A");
    Competition c3("Comp B", "comp_b", "Site B");

    EXPECT_EQ(c1, c2);
    EXPECT_NE(c1, c3);
}

TEST(CompetitionTest, TournamentAliasWorks) {
    Tournament tournament("National Tournament", "nat_tourn_2026", "Dallas");
    EXPECT_EQ(tournament.GetName(), "National Tournament");
    EXPECT_EQ(tournament.GetSlug(), "nat_tourn_2026");
    EXPECT_EQ(tournament.GetSite(), "Dallas");

    ScheduledGame game(
        "R1 M1 G1", {"Team 1", "Team 2"}, {}, 1000LL, 2000LL,
        1, 1, 1, "G", std::nullopt, 1050LL);
    ASSERT_TRUE(game.GetActualStartTimeMs().has_value());
    EXPECT_EQ(*game.GetActualStartTimeMs(), 1050LL);
    tournament.AddScheduledGame(game);
    EXPECT_EQ(tournament.GetSchedule().size(), 1u);
}

}  // namespace
}  // namespace live_renderer

