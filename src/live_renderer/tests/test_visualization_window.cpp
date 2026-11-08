#include <gtest/gtest.h>
#include "live_renderer/state/mock_game_state.hpp"
#include "live_renderer/windows/visualization_window.hpp"

using namespace live_renderer;

TEST(VisualizationWindowTest, CoordinateTransformation) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.title = "Test Window";
    // 16:9 window: 1920x1080 -> unit_w = 1080 * 16 / 9 = 1920
    wcfg.rect = {0, 0, 1920, 1080};

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    std::array<float, 4> rel_rect{0.25f, 0.50f, 0.50f, 0.25f};
    auto px_rect = win.RelativeToPixelRect(rel_rect);

    EXPECT_FLOAT_EQ(px_rect[0], 480.0f);
    EXPECT_FLOAT_EQ(px_rect[1], 540.0f);
    EXPECT_FLOAT_EQ(px_rect[2], 960.0f);
    EXPECT_FLOAT_EQ(px_rect[3], 270.0f);

    // Non-16:9 window: 1000x900 -> height 900, so unit_w = 900 * 16 / 9 = 1600
    WindowConfig wcfg2;
    wcfg2.rect = {0, 0, 1000, 900};
    VisualizationWindow win2(wcfg2, ui);
    auto px_rect2 = win2.RelativeToPixelRect({1.0f, 1.0f, 0.5f, 0.5f});
    EXPECT_FLOAT_EQ(px_rect2[0], 1600.0f);
    EXPECT_FLOAT_EQ(px_rect2[1], 900.0f);
    EXPECT_FLOAT_EQ(px_rect2[2], 800.0f);
    EXPECT_FLOAT_EQ(px_rect2[3], 450.0f);
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

    // 1 header element + 5 players * 2 elements + 1 totals row
    // (score only, no "TOTALS" for name) = 12 commands
    ASSERT_EQ(batch.commands.size(), 12u);
    EXPECT_EQ(batch.commands[0].text, "ROSTER");

    // First player name
    EXPECT_EQ(batch.commands[1].text, "AlphaCommander");
    EXPECT_EQ(batch.commands[2].text, "8200");

    // Last player is dummy totals row with score only, no TOTALS text
    EXPECT_EQ(batch.commands[11].text, "24500");
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

    // Highlight element index 0 (4 borders + 1 corner handle = 5 extra
    // SolidQuad commands; no fill rectangle).
    auto highlight_batch = win.GenerateBatch(state, 0, 0);
    ASSERT_EQ(highlight_batch.commands.size(), 6u);
    EXPECT_EQ(highlight_batch.commands[0].type, RenderCommand::Type::Text);

    // Verify all 5 extra commands are solid quads with orange border color
    for (size_t i = 1; i <= 5; ++i) {
        EXPECT_EQ(
            highlight_batch.commands[i].type, RenderCommand::Type::SolidQuad);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[0], 1.0f);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[1], 0.55f);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[2], 0.0f);
        EXPECT_FLOAT_EQ(highlight_batch.commands[i].color_rgba[3], 1.0f);
    }

    // Verify none of the commands fill the element's interior rect
    const float unit_w = 1000.0f * 16.0f / 9.0f;
    for (size_t i = 1; i <= 5; ++i) {
        bool matches_full_rect =
            (highlight_batch.commands[i].pixel_rect[0] == 0.1f * unit_w &&
             highlight_batch.commands[i].pixel_rect[1] == 200.0f &&
             highlight_batch.commands[i].pixel_rect[2] == 0.3f * unit_w &&
             highlight_batch.commands[i].pixel_rect[3] == 400.0f);
        EXPECT_FALSE(matches_full_rect);
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
        const float unit_w = 800.0f * 16.0f / 9.0f;
        EXPECT_FLOAT_EQ(cmd.container_rect[0], 0.1f * unit_w);
        EXPECT_FLOAT_EQ(cmd.container_rect[1], 160.0f);
        EXPECT_FLOAT_EQ(cmd.container_rect[2], 0.8f * unit_w);
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

TEST(VisualizationWindowTest, DefaultFontInheritanceAndOverride) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1280, 800};

    ElementConfig text_default;
    text_default.type = "user_text";
    text_default.text = "Inherited Font Text";
    text_default.font = "default";
    text_default.rect = {0.1f, 0.1f, 0.8f, 0.1f};
    wcfg.elements.push_back(text_default);

    ElementConfig text_override;
    text_override.type = "user_text";
    text_override.text = "Overridden Font Text";
    text_override.font = "Consolas";
    text_override.rect = {0.1f, 0.3f, 0.8f, 0.1f};
    wcfg.elements.push_back(text_override);

    UIConfig ui;
    ui.default_font = "Verdana";
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 1000);

    ASSERT_EQ(batch.commands.size(), 2u);
    EXPECT_EQ(batch.commands[0].font, "Verdana");
    EXPECT_EQ(batch.commands[1].font, "Consolas");
}

TEST(VisualizationWindowTest, GameScorecardsVerticalListLayout) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1280, 800};

    ElementConfig game_sc;
    game_sc.type = "game_scorecard";
    game_sc.orientation = "vertical";
    game_sc.rect = {0.1f, 0.1f, 0.8f, 0.8f};
    game_sc.vertical_spacing = 10.0f;
    wcfg.elements.push_back(game_sc);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 1000);

    float min_team1_y = 9999.0f;
    float max_team1_y = -9999.0f;
    float min_team2_y = 9999.0f;

    for (const auto& cmd : batch.commands) {
        if (cmd.text == "AlphaCommander" || cmd.text == "FireHeavy") {
            min_team1_y = std::min(min_team1_y, cmd.pixel_rect[1]);
            max_team1_y = std::max(max_team1_y, cmd.pixel_rect[1]);
        }
        if (cmd.text == "BravoScout" || cmd.text == "EarthAmmo") {
            min_team2_y = std::min(min_team2_y, cmd.pixel_rect[1]);
        }
    }

    EXPECT_GT(min_team2_y, max_team1_y);
}

TEST(VisualizationWindowTest, ImportantGameMessagesRendering) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 1000};

    ElementConfig msgs;
    msgs.type = "important_game_messages";
    msgs.rect = {0.1f, 0.2f, 0.8f, 0.4f};
    msgs.lines = 3;
    msgs.display_time = 4.0f;
    msgs.fadeout_time = 1.0f;
    wcfg.elements.push_back(msgs);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    GameStateSnapshot state;
    state.in_session = true;
    state.important_events = {
        {10, 1000, "Commander activates nuke"}
    };

    auto batch = win.GenerateBatch(state, 1000);
    bool found_msg = false;
    for (const auto& cmd : batch.commands) {
        if (cmd.text.find("Commander activates nuke") != std::string::npos) {
            found_msg = true;
            EXPECT_NEAR(cmd.opacity, 1.0f, 0.05f);
            EXPECT_GE(cmd.pixel_rect[1], 200.0f);
        }
    }
    EXPECT_TRUE(found_msg);

    // Fadeout at t=5500
    auto fade_batch = win.GenerateBatch(state, 5500);
    bool found_fading = false;
    for (const auto& cmd : fade_batch.commands) {
        if (cmd.text.find("Commander activates nuke") != std::string::npos) {
            found_fading = true;
            EXPECT_LT(cmd.opacity, 0.8f);
            EXPECT_GT(cmd.opacity, 0.2f);
        }
    }
    EXPECT_TRUE(found_fading);
}

TEST(VisualizationWindowTest, SeparateTeamAndPlayerRankingsAnimation) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1000, 800};

    ElementConfig sc;
    sc.type = "game_scorecard";
    sc.rect = {0.1f, 0.1f, 0.8f, 0.8f};
    sc.orientation = "horizontal";
    // Team animation is linear 1.0s, but player ranking animation is none!
    sc.team_change_animation = "linear";
    sc.team_animation_duration = 1.0f;
    sc.player_change_animation = "none";
    wcfg.elements.push_back(sc);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state1 = MockGameState::CreateMockSM5State();
    auto batch1 = win.GenerateBatch(state1, 0, -1);

    // Swap players in team 1 at t=1000
    auto state2 = state1;
    state2.player_rankings_by_team[1] = {12, 11, 13, 14, 15};
    // Swap teams order: team 2 first, team 1 second
    state2.team_rankings = {2, 1};

    // At t=1500 (halfway for teams):
    auto batch2 = win.GenerateBatch(state2, 1500, -1);

    // With player_change_animation as "none", player 12 snaps immediately
    float y11_p2 = -1.0f;
    float y12_p2 = -1.0f;
    for (const auto& cmd : batch2.commands) {
        if (cmd.text == "AlphaCommander") y11_p2 = cmd.pixel_rect[1];
        if (cmd.text == "FireHeavy") y12_p2 = cmd.pixel_rect[1];
    }
    // Player 12 is top player, so y12 < y11 immediately without waiting 1.0s
    EXPECT_LT(y12_p2, y11_p2);
}

TEST(VisualizationWindowTest, UserImageWithFitModeAndOpacity) {
    WindowConfig wcfg;
    wcfg.id = 8;
    wcfg.title = "Image Window";
    wcfg.rect = {0, 0, 1600, 900};

    ElementConfig img;
    img.type = "user_image";
    img.rect = {0.1f, 0.2f, 0.4f, 0.3f};
    img.image_file = "assets/ball.png";
    img.opacity = 0.75f;
    img.fit = "crop";
    wcfg.elements.push_back(img);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 0, -1);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/ball.png");
    EXPECT_FLOAT_EQ(batch.commands[0].opacity, 0.75f);
    EXPECT_EQ(batch.commands[0].fit, "crop");
    EXPECT_FALSE(batch.commands[0].is_movie);
}

TEST(VisualizationWindowTest, MovieComponentGeneratesMovieCommand) {
    WindowConfig wcfg;
    wcfg.id = 9;
    wcfg.title = "Movie Window";
    wcfg.rect = {0, 0, 1600, 900};

    ElementConfig movie;
    movie.type = "movie";
    movie.rect = {0.2f, 0.2f, 0.5f, 0.5f};
    movie.movie_file = "assets/intro.gif";
    movie.opacity = 0.9f;
    movie.fit = "scale";
    movie.playback_speed = 1.25f;
    wcfg.elements.push_back(movie);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state, 0, -1);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/intro.gif");
    EXPECT_FLOAT_EQ(batch.commands[0].opacity, 0.9f);
    EXPECT_EQ(batch.commands[0].fit, "scale");
    EXPECT_TRUE(batch.commands[0].is_movie);
    EXPECT_FLOAT_EQ(batch.commands[0].playback_speed, 1.25f);
}

TEST(VisualizationWindowTest, ImageAndMovieTintTeamColorInScorecard) {
    UIConfig ui;

    // Header template with image and movie tinted by team color
    TemplateConfig header_tmpl;
    header_tmpl.id = 1;
    header_tmpl.type = "scorecard_header_row";

    ElementConfig h_img;
    h_img.type = "user_image";
    h_img.image_file = "assets/badge.png";
    h_img.tint_team_color = 1.0f;
    h_img.rect = {0.0f, 0.0f, 0.2f, 1.0f};
    header_tmpl.elements.push_back(h_img);

    ElementConfig h_movie;
    h_movie.type = "movie";
    h_movie.movie_file = "assets/fire.gif";
    h_movie.tint_team_color = 0.5f;
    h_movie.rect = {0.2f, 0.0f, 0.2f, 1.0f};
    header_tmpl.elements.push_back(h_movie);

    ui.templates.push_back(header_tmpl);

    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1280, 800};

    ElementConfig sc;
    sc.type = "team_scorecard";
    sc.team_index = 1; // Team 1 is Fire (#FF5000: 1.0, 80/255=0.3137, 0.0)
    sc.header_template_id = 1;
    sc.rect = {0.0f, 0.0f, 1.0f, 1.0f};
    wcfg.elements.push_back(sc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    ASSERT_GE(batch.commands.size(), 2u);

    // Command 0 is h_img tinted with 100% Fire team color (#FF5000)
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/badge.png");
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 1.0f);
    EXPECT_NEAR(batch.commands[0].color_rgba[1], 80.0f / 255.0f, 0.01f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 0.0f);

    // Command 1 is h_movie tinted with 50% Fire team color
    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[1].texture_asset, "assets/fire.gif");
    EXPECT_TRUE(batch.commands[1].is_movie);
    EXPECT_FLOAT_EQ(batch.commands[1].color_rgba[0], 1.0f);
    EXPECT_NEAR(
        batch.commands[1].color_rgba[1],
        1.0f + 0.5f * (80.0f / 255.0f - 1.0f),
        0.01f);
    EXPECT_FLOAT_EQ(batch.commands[1].color_rgba[2], 0.5f);
}

TEST(VisualizationWindowTest, TopLevelImageWithTeamTint) {
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1280, 800};

    ElementConfig img;
    img.type = "user_image";
    img.image_file = "assets/emblem.png";
    img.team_index = 1;
    img.tint_team_color = 1.0f;
    img.rect = {0.1f, 0.1f, 0.3f, 0.3f};
    wcfg.elements.push_back(img);

    UIConfig ui;
    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/emblem.png");
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 1.0f);
    EXPECT_NEAR(batch.commands[0].color_rgba[1], 80.0f / 255.0f, 0.01f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 0.0f);
}

TEST(VisualizationWindowTest,
     ScorecardTemplateElementsXOffsetUnaffectedByContainerWidthOrHeight) {
    UIConfig ui;

    TemplateConfig header_tmpl;
    header_tmpl.id = 1;
    header_tmpl.type = "scorecard_header_row";
    ElementConfig h_text;
    h_text.type = "user_text";
    h_text.text = "ROSTER";
    h_text.rect = {0.05f, 0.0f, 0.40f, 1.0f};
    header_tmpl.elements.push_back(h_text);
    ui.templates.push_back(header_tmpl);

    TemplateConfig row_tmpl;
    row_tmpl.id = 2;
    row_tmpl.type = "scorecard_row";

    ElementConfig p_name;
    p_name.type = "player_name";
    p_name.rect = {0.05f, 0.0f, 0.30f, 1.0f};
    row_tmpl.elements.push_back(p_name);

    ElementConfig p_score;
    p_score.type = "player_score";
    p_score.rect = {0.40f, 0.0f, 0.20f, 1.0f};
    row_tmpl.elements.push_back(p_score);
    ui.templates.push_back(row_tmpl);

    // First window with container width = 0.50f, height = 0.40f
    WindowConfig wcfg1;
    wcfg1.id = 1;
    wcfg1.rect = {0, 0, 1600, 900};
    ElementConfig sc1;
    sc1.type = "team_scorecard";
    sc1.team_index = 1;
    sc1.header_template_id = 1;
    sc1.row_template_id = 2;
    sc1.rect = {0.10f, 0.10f, 0.50f, 0.40f};
    wcfg1.elements.push_back(sc1);

    // Second window with same x, y, but different container width = 0.85f,
    // and different container height = 0.75f
    WindowConfig wcfg2;
    wcfg2.id = 2;
    wcfg2.rect = {0, 0, 1600, 900};
    ElementConfig sc2;
    sc2.type = "team_scorecard";
    sc2.team_index = 1;
    sc2.header_template_id = 1;
    sc2.row_template_id = 2;
    sc2.rect = {0.10f, 0.10f, 0.85f, 0.75f};
    wcfg2.elements.push_back(sc2);

    VisualizationWindow win1(wcfg1, ui);
    VisualizationWindow win2(wcfg2, ui);

    auto state = MockGameState::CreateMockSM5State();
    auto batch1 = win1.GenerateBatch(state);
    auto batch2 = win2.GenerateBatch(state);

    ASSERT_EQ(batch1.commands.size(), batch2.commands.size());
    ASSERT_FALSE(batch1.commands.empty());

    const float win_h = 900.0f;
    const float unit_w = win_h * 16.0f / 9.0f;  // 1600.0f
    const float expected_header_x = (sc1.rect[0] + h_text.rect[0]) * unit_w;
    const float expected_header_w = h_text.rect[2] * unit_w;
    const float expected_name_x = (sc1.rect[0] + p_name.rect[0]) * unit_w;
    const float expected_name_w = p_name.rect[2] * unit_w;
    const float expected_score_x = (sc1.rect[0] + p_score.rect[0]) * unit_w;
    const float expected_score_w = p_score.rect[2] * unit_w;

    // Header command
    EXPECT_FLOAT_EQ(batch1.commands[0].pixel_rect[0], expected_header_x);
    EXPECT_FLOAT_EQ(batch1.commands[0].pixel_rect[2], expected_header_w);
    EXPECT_FLOAT_EQ(batch2.commands[0].pixel_rect[0], expected_header_x);
    EXPECT_FLOAT_EQ(batch2.commands[0].pixel_rect[2], expected_header_w);

    // First player row commands (name at index 1, score at index 2)
    EXPECT_FLOAT_EQ(batch1.commands[1].pixel_rect[0], expected_name_x);
    EXPECT_FLOAT_EQ(batch1.commands[1].pixel_rect[2], expected_name_w);
    EXPECT_FLOAT_EQ(batch2.commands[1].pixel_rect[0], expected_name_x);
    EXPECT_FLOAT_EQ(batch2.commands[1].pixel_rect[2], expected_name_w);

    EXPECT_FLOAT_EQ(batch1.commands[2].pixel_rect[0], expected_score_x);
    EXPECT_FLOAT_EQ(batch1.commands[2].pixel_rect[2], expected_score_w);
    EXPECT_FLOAT_EQ(batch2.commands[2].pixel_rect[0], expected_score_x);
    EXPECT_FLOAT_EQ(batch2.commands[2].pixel_rect[2], expected_score_w);
}

TEST(VisualizationWindowTest, RendersTeamScorecardBackgroundUnderneath) {
    UIConfig ui;
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig sc;
    sc.type = "team_scorecard";
    sc.team_index = 1;
    sc.rect = {0.1f, 0.1f, 0.5f, 0.8f};
    sc.background.enabled = true;
    sc.background.color = "#FF0000";
    sc.background.image_file = "assets/bg.png";
    sc.background.movie_file = "assets/bg.mp4";
    sc.background.fit = "crop";
    sc.background.playback_speed = 1.2f;
    sc.background.tint_team_color = 0.5f;
    sc.background.opacity = 0.8f;
    sc.background.corner_radius = 16.0f;
    wcfg.elements.push_back(sc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    // Commands should start with background commands immediately underneath:
    // 1. Solid quad with color #FF0000 and 0.8 opacity
    ASSERT_GE(batch.commands.size(), 3u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 1.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[1], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[3], 0.8f);
    EXPECT_FLOAT_EQ(batch.commands[0].corner_radius, 16.0f);

    // 2. Video quad
    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::TexturedQuad);
    EXPECT_TRUE(batch.commands[1].is_movie);
    EXPECT_EQ(batch.commands[1].texture_asset, "assets/bg.mp4");
    EXPECT_EQ(batch.commands[1].fit, "crop");
    EXPECT_FLOAT_EQ(batch.commands[1].playback_speed, 1.2f);
    EXPECT_FLOAT_EQ(batch.commands[1].opacity, 0.8f);
    EXPECT_FLOAT_EQ(batch.commands[1].corner_radius, 16.0f);

    // 3. Image quad
    EXPECT_EQ(batch.commands[2].type, RenderCommand::Type::TexturedQuad);
    EXPECT_FALSE(batch.commands[2].is_movie);
    EXPECT_EQ(batch.commands[2].texture_asset, "assets/bg.png");
    EXPECT_EQ(batch.commands[2].fit, "crop");
    EXPECT_FLOAT_EQ(batch.commands[2].opacity, 0.8f);
    EXPECT_FLOAT_EQ(batch.commands[2].corner_radius, 16.0f);
}

TEST(VisualizationWindowTest, RendersGameScorecardBackgroundOnceUnderneath) {
    UIConfig ui;
    WindowConfig wcfg;
    wcfg.id = 2;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig gsc;
    gsc.type = "game_scorecard";
    gsc.rect = {0.05f, 0.05f, 0.9f, 0.9f};
    gsc.background.enabled = true;
    gsc.background.color = "#0000FF";
    gsc.background.opacity = 1.0f;
    gsc.background.corner_radius = 10.0f;
    wcfg.elements.push_back(gsc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    ASSERT_GE(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[1], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 1.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].corner_radius, 10.0f);
}

TEST(VisualizationWindowTest, GameScorecardRendersBothOuterAndTeamBackgrounds) {
    UIConfig ui;
    WindowConfig wcfg;
    wcfg.id = 2;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig gsc;
    gsc.type = "game_scorecard";
    gsc.rect = {0.05f, 0.05f, 0.9f, 0.9f};
    gsc.background.enabled = true;
    gsc.background.color = "#0000FF";
    gsc.background.opacity = 1.0f;
    gsc.background.corner_radius = 10.0f;

    gsc.team_background.enabled = true;
    gsc.team_background.color = "#00FF00";
    gsc.team_background.opacity = 0.8f;
    gsc.team_background.tint_team_color = 0.5f;
    gsc.team_background.corner_radius = 4.0f;
    wcfg.elements.push_back(gsc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    ASSERT_GE(batch.commands.size(), 3u);
    // Command 0 is outer game scorecard background
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[1], 0.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 1.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].corner_radius, 10.0f);

    // Command 1 is the first team's team background
    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::SolidQuad);
    EXPECT_FLOAT_EQ(batch.commands[1].corner_radius, 4.0f);
    EXPECT_FLOAT_EQ(batch.commands[1].color_rgba[3], 0.8f);
}

TEST(VisualizationWindowTest, DisabledBackgroundProducesNoCommands) {
    UIConfig ui;
    WindowConfig wcfg;
    wcfg.id = 2;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig sc;
    sc.type = "team_scorecard";
    sc.rect = {0.05f, 0.05f, 0.4f, 0.8f};
    sc.team_index = 1;
    sc.background.enabled = false;
    sc.background.color = "#FF0000";
    sc.background.image_file = "assets/bg.png";
    sc.background.movie_file = "assets/bg.mp4";
    wcfg.elements.push_back(sc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    for (const auto& cmd : batch.commands) {
        if (cmd.type == RenderCommand::Type::SolidQuad) {
            const bool is_bg =
                (std::abs(cmd.color_rgba[0] - 1.0f) < 0.01f &&
                 std::abs(cmd.color_rgba[1] - 0.0f) < 0.01f &&
                 std::abs(cmd.color_rgba[2] - 0.0f) < 0.01f);
            EXPECT_FALSE(is_bg);
        }
    }
}

TEST(VisualizationWindowTest, OnlyOneTotalsRowPerActiveTeam) {
    UIConfig ui;
    WindowConfig wcfg;
    wcfg.id = 3;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig gsc;
    gsc.type = "game_scorecard";
    gsc.rect = {0.05f, 0.05f, 0.9f, 0.9f};
    gsc.add_totals = true;
    wcfg.elements.push_back(gsc);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();

    // Add Neutral team with 0 players and a dummy player
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
    d3.score = 0;
    state.players[103] = d3;

    auto batch = win.GenerateBatch(state);

    // Count how many score commands correspond to dummy player scores:
    // Fire dummy (101) score is 24500, Earth dummy (102) score is 21800.
    int fire_totals_count = 0;
    int earth_totals_count = 0;
    int neutral_totals_count = 0;
    for (const auto& cmd : batch.commands) {
        if (cmd.text == "24500") ++fire_totals_count;
        if (cmd.text == "21800") ++earth_totals_count;
        if (cmd.text == "0" && cmd.hex_color == "#808080") {
            ++neutral_totals_count;
        }
    }

    EXPECT_EQ(fire_totals_count, 1);
    EXPECT_EQ(earth_totals_count, 1);
    EXPECT_EQ(neutral_totals_count, 0);
}

TEST(VisualizationWindowTest, TeamRosterRendersPlayerProfileTemplate) {
    UIConfig ui;

    TemplateConfig tmpl;
    tmpl.id = 10;
    tmpl.name = "Custom Player Profile";
    tmpl.type = "player_profile";
    tmpl.size = {1.0f, 1.0f};

    ElementConfig name_el;
    name_el.type = "player_name";
    name_el.rect = {0.0f, 0.0f, 1.0f, 0.3f};
    tmpl.elements.push_back(name_el);

    ElementConfig pic_el;
    pic_el.type = "player_profile_picture";
    pic_el.rect = {0.0f, 0.3f, 1.0f, 0.7f};
    tmpl.elements.push_back(pic_el);

    ui.templates.push_back(tmpl);

    WindowConfig wcfg;
    wcfg.id = 4;
    wcfg.rect = {0, 0, 1600, 800};

    ElementConfig roster;
    roster.type = "team_roster";
    roster.rect = {0.1f, 0.1f, 0.3f, 0.8f};
    roster.team_index = 1;
    roster.player_profile_template_id = 10;
    wcfg.elements.push_back(roster);

    VisualizationWindow win(wcfg, ui);
    auto state = MockGameState::CreateMockSM5State();
    auto batch = win.GenerateBatch(state);

    bool has_alpha = false;
    bool has_fire_heavy = false;
    int profile_pic_count = 0;
    for (const auto& cmd : batch.commands) {
        if (cmd.text.find("Alpha") != std::string::npos) {
            has_alpha = true;
        }
        if (cmd.text.find("FireHeavy") != std::string::npos) {
            has_fire_heavy = true;
        }
        if (cmd.type == RenderCommand::Type::TexturedQuad &&
            cmd.texture_asset == "assets/sm5/commander.png") {
            ++profile_pic_count;
        }
    }

    EXPECT_TRUE(has_alpha);
    EXPECT_TRUE(has_fire_heavy);
    EXPECT_GE(profile_pic_count, 5);
}







