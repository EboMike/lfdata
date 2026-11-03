#include <gtest/gtest.h>
#include "live_renderer/state/mock_game_state.hpp"
#include "live_renderer/windows/visualization_window.hpp"

using namespace live_renderer;

TEST(VisualizationWindowTest, CoordinateTransformation) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.title = "Test Window";
    wcfg.rect = {0, 0, 1920, 1080};

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    std::array<float, 4> rel_rect{0.25f, 0.50f, 0.50f, 0.25f};
    auto px_rect = win.RelativeToPixelRect(rel_rect);

    EXPECT_FLOAT_EQ(px_rect[0], 480.0f);
    EXPECT_FLOAT_EQ(px_rect[1], 540.0f);
    EXPECT_FLOAT_EQ(px_rect[2], 960.0f);
    EXPECT_FLOAT_EQ(px_rect[3], 270.0f);
}

TEST(VisualizationWindowTest, GeneratesTextAndTimerCommands) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1280, 800};

    ElementConfig text_el;
    text_el.type = "user_text";
    text_el.text = "Arena: {center} - Game: {game_type}";
    text_el.rect = {0.1f, 0.05f, 0.8f, 0.1f};
    text_el.font_size = 20.0f;
    wcfg.elements.push_back(text_el);

    ElementConfig timer_el;
    timer_el.type = "game_timer";
    timer_el.rect = {0.4f, 0.0f, 0.2f, 0.08f};
    timer_el.font_size = 32.0f;
    wcfg.elements.push_back(timer_el);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 100000);

    ASSERT_EQ(batch.commands.size(), 2u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[0].text, "Arena: Loveland - Game: SM5");
    EXPECT_FLOAT_EQ(batch.commands[0].font_size_px, 20.0f); // 20 at 800px height is 20px

    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::Text);
    EXPECT_FALSE(batch.commands[1].text.empty());
    EXPECT_FLOAT_EQ(batch.commands[1].font_size_px, 32.0f);
}

TEST(VisualizationWindowTest, GeneratesScorecardWithTemplateRows) {
    UIConfig ui;

    TemplateConfig header_tmpl;
    header_tmpl.id = 1;
    header_tmpl.type = "scorecard_header_row";
    ElementConfig h_text;
    h_text.type = "user_text";
    h_text.text = "ROSTER";
    h_text.rect = {0.0f, 0.0f, 1.0f, 1.0f};
    header_tmpl.elements.push_back(h_text);
    ui.templates.push_back(header_tmpl);

    TemplateConfig row_tmpl;
    row_tmpl.id = 2;
    row_tmpl.type = "scorecard_row";

    ElementConfig p_name;
    p_name.type = "player_name";
    p_name.rect = {0.0f, 0.0f, 0.5f, 1.0f};
    row_tmpl.elements.push_back(p_name);

    ElementConfig p_score;
    p_score.type = "player_score";
    p_score.rect = {0.5f, 0.0f, 0.5f, 1.0f};
    row_tmpl.elements.push_back(p_score);
    ui.templates.push_back(row_tmpl);

    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 1000};

    ElementConfig sc_el;
    sc_el.type = "team_scorecard";
    sc_el.team_index = 1; // Fire team
    sc_el.header_template_id = 1;
    sc_el.row_template_id = 2;
    sc_el.add_totals = true;
    sc_el.rect = {0.05f, 0.10f, 0.90f, 0.80f};
    wcfg.elements.push_back(sc_el);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    // 1 header element + 6 players (5 players + 1 dummy) * 2 elements per row = 1 + 12 = 13 commands
    ASSERT_EQ(batch.commands.size(), 13u);
    EXPECT_EQ(batch.commands[0].text, "ROSTER");

    // First player name
    EXPECT_EQ(batch.commands[1].text, "AlphaCommander");
    EXPECT_EQ(batch.commands[2].text, "8200");

    // Last player is dummy totals row
    EXPECT_EQ(batch.commands[11].text, "TOTALS");
    EXPECT_EQ(batch.commands[12].text, "24500");
}

TEST(VisualizationWindowTest, HighlightElementAppendsHighlightCommands) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 1000};

    ElementConfig text_el;
    text_el.type = "user_text";
    text_el.text = "Hello World";
    text_el.rect = {0.1f, 0.2f, 0.3f, 0.4f};
    wcfg.elements.push_back(text_el);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();

    // No highlight
    auto normal_batch = win.GenerateBatch(state, 0, -1);
    ASSERT_EQ(normal_batch.commands.size(), 1u);

    // Highlight element index 0 (fill overlay + 4 borders = 5 extra SolidQuad commands)
    auto highlight_batch = win.GenerateBatch(state, 0, 0);
    ASSERT_EQ(highlight_batch.commands.size(), 6u);
    EXPECT_EQ(highlight_batch.commands[0].type, RenderCommand::Type::Text);

    // Check highlight fill command
    EXPECT_EQ(highlight_batch.commands[1].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[0], 100.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[1], 200.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[2], 300.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[3], 400.0f);

    // Check borders are solid quads
    for (size_t i = 2; i <= 5; ++i) {
        EXPECT_EQ(highlight_batch.commands[i].type, RenderCommand::Type::SolidQuad);
    }
}

TEST(VisualizationWindowTest, RespectsZPositionOrdering) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 1000};

    // First defined element has higher Z (should render second / on top)
    ElementConfig el_top;
    el_top.type = "user_text";
    el_top.text = "Top Text";
    el_top.z_position = 10;
    wcfg.elements.push_back(el_top);

    // Second defined element has lower Z (should render first / underneath)
    ElementConfig el_bottom;
    el_bottom.type = "user_text";
    el_bottom.text = "Bottom Text";
    el_bottom.z_position = -1;
    wcfg.elements.push_back(el_bottom);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();

    auto batch = win.GenerateBatch(state, 0, -1);
    ASSERT_EQ(batch.commands.size(), 2u);
    EXPECT_EQ(batch.commands[0].text, "Bottom Text");
    EXPECT_EQ(batch.commands[1].text, "Top Text");
}



