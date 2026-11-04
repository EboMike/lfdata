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

    // Highlight element index 0 (fill overlay + 4 borders + 1 corner handle = 6 extra SolidQuad commands)
    auto highlight_batch = win.GenerateBatch(state, 0, 0);
    ASSERT_EQ(highlight_batch.commands.size(), 7u);
    EXPECT_EQ(highlight_batch.commands[0].type, RenderCommand::Type::Text);

    // Check highlight fill command is orange
    EXPECT_EQ(highlight_batch.commands[1].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[0], 100.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[1], 200.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[2], 300.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].pixel_rect[3], 400.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].color_rgba[0], 1.0f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].color_rgba[1], 0.55f);
    EXPECT_FLOAT_EQ(highlight_batch.commands[1].color_rgba[2], 0.0f);

    // Check borders and corner handle are solid quads with orange color
    for (size_t i = 2; i <= 6; ++i) {
        EXPECT_EQ(highlight_batch.commands[i].type, RenderCommand::Type::SolidQuad);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[0], 1.0f);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[1], 0.55f);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[2], 0.0f);
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

TEST(VisualizationWindowTest, EventScrollerPropertiesAndTilt) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 800};

    ElementConfig scroller;
    scroller.type = "event_scroller";
    scroller.rect = {0.1f, 0.2f, 0.8f, 0.6f};
    scroller.font = "roboto";
    scroller.font_size = 24.0f;
    scroller.alignment = "center";
    scroller.tilt = 15.0f;
    wcfg.elements.push_back(scroller);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    GameStateSnapshot state;
    state.in_session = false;
    state.event_scroller = {
        {1000, "Alpha zapped Beta"},
        {2000, "Beta destroyed Base"}
    };

    auto batch = win.GenerateBatch(state, 0, -1);
    ASSERT_EQ(batch.commands.size(), 2u);

    for (const auto& cmd : batch.commands) {
        EXPECT_EQ(cmd.type, RenderCommand::Type::Text);
        EXPECT_EQ(cmd.font, "roboto");
        EXPECT_FLOAT_EQ(cmd.font_size_px, 24.0f);
        EXPECT_EQ(cmd.alignment, "center");
        EXPECT_FLOAT_EQ(cmd.tilt_deg, 15.0f);
        EXPECT_TRUE(cmd.clip_to_container);
        EXPECT_FLOAT_EQ(cmd.container_rect[0], 100.0f);
        EXPECT_FLOAT_EQ(cmd.container_rect[1], 160.0f);
        EXPECT_FLOAT_EQ(cmd.container_rect[2], 800.0f);
        EXPECT_FLOAT_EQ(cmd.container_rect[3], 480.0f);
    }
}

TEST(VisualizationWindowTest, RendersTemplateElementsAndPlayerRoleDirectly) {
    WindowConfig wcfg;
    wcfg.id = 99;
    wcfg.title = "Template Window";
    wcfg.rect = {0, 0, 800, 200};

    ElementConfig role_el;
    role_el.type = "player_role";
    role_el.rect = {0.05f, 0.1f, 0.2f, 0.8f};
    wcfg.elements.push_back(role_el);

    ElementConfig name_el;
    name_el.type = "player_name";
    name_el.rect = {0.3f, 0.1f, 0.6f, 0.8f};
    wcfg.elements.push_back(name_el);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 0, -1);

    ASSERT_GE(batch.commands.size(), 2u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/sm5/commander.png");

    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[1].text, "AlphaCommander");
}

TEST(VisualizationWindowTest, AnimatesListOrderChanges) {
    WindowConfig wcfg;
    wcfg.id = 5;
    wcfg.title = "Scorecard Animation";
    wcfg.rect = {0, 0, 800, 600};

    ElementConfig sc;
    sc.type = "team_scorecard";
    sc.team_index = 1;
    sc.rect = {0.1f, 0.1f, 0.8f, 0.8f};
    sc.change_animation = "linear";
    sc.animation_duration = 1.0f;
    wcfg.elements.push_back(sc);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    // Initial state: team 1 players rankings: 11, 12, 13, 14, 15
    auto state1 = MockGameState::CreateMockSM5State();
    auto batch1 = win.GenerateBatch(state1, 0, -1);

    float y11_initial = -1.0f;
    float y12_initial = -1.0f;
    for (const auto& cmd : batch1.commands) {
        if (cmd.text == "AlphaCommander") y11_initial = cmd.pixel_rect[1];
        if (cmd.text == "FireHeavy") y12_initial = cmd.pixel_rect[1];
    }
    ASSERT_GT(y11_initial, 0.0f);
    ASSERT_GT(y12_initial, y11_initial);

    // Swap rankings: player 12 is first, player 11 is second at t = 1000
    auto state2 = state1;
    state2.player_rankings_by_team[1] = {12, 11, 13, 14, 15};
    win.GenerateBatch(state2, 1000, -1);

    // Halfway through animation (t = 1500, elapsed = 500ms out of 1000ms)
    auto batch2 = win.GenerateBatch(state2, 1500, -1);
    float y11_mid = -1.0f;
    float y12_mid = -1.0f;
    for (const auto& cmd : batch2.commands) {
        if (cmd.text == "AlphaCommander") y11_mid = cmd.pixel_rect[1];
        if (cmd.text == "FireHeavy") y12_mid = cmd.pixel_rect[1];
    }
    float expected_mid = (y11_initial + y12_initial) * 0.5f;
    EXPECT_NEAR(y11_mid, expected_mid, 1.0f);
    EXPECT_NEAR(y12_mid, expected_mid, 1.0f);

    // End of animation (t = 2000, elapsed = 1000ms)
    auto batch3 = win.GenerateBatch(state2, 2000, -1);
    float y11_final = -1.0f;
    float y12_final = -1.0f;
    for (const auto& cmd : batch3.commands) {
        if (cmd.text == "AlphaCommander") y11_final = cmd.pixel_rect[1];
        if (cmd.text == "FireHeavy") y12_final = cmd.pixel_rect[1];
    }
    EXPECT_FLOAT_EQ(y11_final, y12_initial);
    EXPECT_FLOAT_EQ(y12_final, y11_initial);
}




