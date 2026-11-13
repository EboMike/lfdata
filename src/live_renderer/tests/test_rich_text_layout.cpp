#include <gtest/gtest.h>
#include "live_renderer/render/rich_text_layout.hpp"

using namespace live_renderer;

TEST(RichTextLayoutTest, PlaceholderSubstitution) {
    GameStateSnapshot state;
    state.game_type = "Laserball";
    state.center_name = "Syracuse";

    std::string text = "Welcome to {game_type} at {center}!";
    std::string res = RichTextLayout::SubstitutePlaceholders(text, state);
    EXPECT_EQ(res, "Welcome to Laserball at Syracuse!");
}

TEST(RichTextLayoutTest, CompetitionPlaceholderSubstitution) {
    GameStateSnapshot state;
    state.competition_name = "LF World Championships 2026";
    state.competition_team_1_name = "Tigers";
    state.competition_team_2_name = "Lions";
    state.next_scheduled_game_team_1_name = "Wolves";
    state.next_scheduled_game_team_2_name = "Bears";

    std::string text = "Tournament: {competition_name} | Now: {competition_team_1_name} vs {competition_team_2_name} | Next: {next_scheduled_game_team_1_name} vs {next_scheduled_game_team_2_name}";
    std::string res = RichTextLayout::SubstitutePlaceholders(text, state);
    EXPECT_EQ(
        res,
        "Tournament: LF World Championships 2026 | Now: Tigers vs Lions | Next: Wolves vs Bears");

    // Empty when none selected / available
    GameStateSnapshot empty_state;
    std::string empty_res = RichTextLayout::SubstitutePlaceholders(text, empty_state);
    EXPECT_EQ(empty_res, "Tournament:  | Now:  vs  | Next:  vs ");
}

TEST(RichTextLayoutTest, ParseMarkupFontColors) {
    std::string raw = "<font color=\"#ff0000\">Alpha</font> zaps <font color=\"#00ff00\">Bravo</font>";
    auto runs = RichTextLayout::ParseMarkup(raw, "#ffffff");

    ASSERT_EQ(runs.size(), 3);
    EXPECT_EQ(runs[0].text, "Alpha");
    EXPECT_EQ(runs[0].hex_color, "#ff0000");

    EXPECT_EQ(runs[1].text, " zaps ");
    EXPECT_EQ(runs[1].hex_color, "#ffffff");

    EXPECT_EQ(runs[2].text, "Bravo");
    EXPECT_EQ(runs[2].hex_color, "#00ff00");
}

TEST(RichTextLayoutTest, ParseMarkupImages) {
    std::string raw = "[img:assets/sm5/commander.png] Alpha";
    auto runs = RichTextLayout::ParseMarkup(raw, "#ffffff");

    ASSERT_EQ(runs.size(), 2);
    EXPECT_TRUE(runs[0].is_image);
    EXPECT_EQ(runs[0].image_asset, "assets/sm5/commander.png");

    EXPECT_FALSE(runs[1].is_image);
    EXPECT_EQ(runs[1].text, " Alpha");
}

TEST(RichTextLayoutTest, FontSizeCalculation) {
    // A font size of 20 takes up 1/40 of an 800px window height
    float px800 = RichTextLayout::ComputePixelFontSize(20.0f, 800.0f);
    EXPECT_FLOAT_EQ(px800, 20.0f);

    float px1600 = RichTextLayout::ComputePixelFontSize(20.0f, 1600.0f);
    EXPECT_FLOAT_EQ(px1600, 40.0f);
}

TEST(RichTextLayoutTest, VerticalSpacingCalculation) {
    float sp800 = RichTextLayout::ComputePixelVerticalSpacing(5.0f, 800.0f);
    EXPECT_FLOAT_EQ(sp800, 5.0f);

    float sp1600 = RichTextLayout::ComputePixelVerticalSpacing(5.0f, 1600.0f);
    EXPECT_FLOAT_EQ(sp1600, 10.0f);

    float sp400 = RichTextLayout::ComputePixelVerticalSpacing(5.0f, 400.0f);
    EXPECT_FLOAT_EQ(sp400, 2.5f);
}

