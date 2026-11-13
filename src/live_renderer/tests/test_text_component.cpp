#include <gtest/gtest.h>
#include "live_renderer/components/text_component.hpp"
#include "live_renderer/render/font_renderer.hpp"
#include "live_renderer/state/mock_game_state.hpp"

using namespace live_renderer;

TEST(TextComponentTest, PlaceholderSubstitution) {
    GameStateSnapshot state;
    state.game_type = "Laserball";
    state.center_name = "Syracuse";

    ElementConfig el;
    el.type = "user_text";
    el.text = "Center: {center} | Type: {game_type}";
    el.font_size = 24.0f;
    el.rect = {0.1f, 0.1f, 0.8f, 0.1f};

    RenderBatch batch;
    TextComponent::GenerateUserTextCommands(el, state, {100.0f, 100.0f, 800.0f, 60.0f}, 800.0f, batch);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[0].text, "Center: Syracuse | Type: Laserball");
    EXPECT_FLOAT_EQ(batch.commands[0].font_size_px, 24.0f);
    EXPECT_TRUE(batch.commands[0].black_outline);
}

TEST(TextComponentTest, CompetitionPlaceholderSubstitution) {
    GameStateSnapshot state;
    state.competition_name = "Brisbane Cup 2026";
    state.competition_team_1_name = "Thunder";
    state.competition_team_2_name = "Lightning";
    state.next_scheduled_game_team_1_name = "Storm";
    state.next_scheduled_game_team_2_name = "Hail";

    ElementConfig el;
    el.type = "user_text";
    el.text = "{competition_name}: {competition_team_1_name} vs {competition_team_2_name} (Next: {next_scheduled_game_team_1_name} vs {next_scheduled_game_team_2_name})";
    el.font_size = 20.0f;
    el.rect = {0.0f, 0.0f, 1.0f, 0.1f};

    RenderBatch batch;
    TextComponent::GenerateUserTextCommands(el, state, {0.0f, 0.0f, 800.0f, 40.0f}, 800.0f, batch);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::Text);
    EXPECT_EQ(
        batch.commands[0].text,
        "Brisbane Cup 2026: Thunder vs Lightning (Next: Storm vs Hail)");
}

TEST(TextComponentTest, ResolvePlayerTextValues) {
    PlayerSnapshot p;
    p.name = "BravoScout";
    p.role = "Scout";
    p.score = 5400;
    p.lives = 8;
    p.shots = 95;
    p.missiles = 2;
    p.special_points = 3;
    p.goals = 1;
    p.assists = 4;
    p.clears = 2;
    p.steals = 6;
    p.blocks = 9;

    EXPECT_EQ(TextComponent::ResolvePlayerText("player_name", p), "BravoScout");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_score", p), "5400");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_lives", p), "8");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_ammo", p), "95");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_missiles", p), "2");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_special_points", p), "3");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_goals", p), "1");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_assists", p), "4");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_clears", p), "2");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_steals", p), "6");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_zaps", p), "9");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_role", p), "Scout");

    // Dummy totals player does not show TOTALS
    PlayerSnapshot dummy;
    dummy.is_dummy = true;
    dummy.score = 25000;
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_name", dummy), "");
    EXPECT_EQ(TextComponent::ResolvePlayerText("player_score", dummy), "25000");

    // Custom text substitution
    std::string custom = "{name} [{role}]: {score} pts, {lives} lives";
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("custom", p, custom),
        "BravoScout [Scout]: 5400 pts, 8 lives");
}

TEST(TextComponentTest, ResolveNewStatsAndPlaceholders) {
    PlayerSnapshot p;
    p.name = "CommanderAlpha";
    p.role = "Commander";
    p.medic_hits = "10/3/-2";
    p.shots_fired = 400;
    p.shots_hit = 100;
    p.accuracy = "25.0%";
    p.missiles_fired = 10;
    p.missiles_landed = 4;
    p.nukes_activated = 2;
    p.nukes_detonated = 1;

    EXPECT_EQ(
        TextComponent::ResolvePlayerText("player_medic_hits", p),
        "10/3/-2");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("player_shots_fired", p),
        "400");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("player_shots_landed", p),
        "100");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("player_accuracy", p),
        "25.0%");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("player_accuracy_string", p),
        "100/400 (25.0%)");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("nukes_activated", p),
        "2");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("nukes_detonated", p),
        "1");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("missiles_fired", p),
        "10");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("missiles_landed", p),
        "4");
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("missile_accuracy_string", p),
        "4/10");

    // Scout role should return empty missile_accuracy_string
    PlayerSnapshot scout;
    scout.role = "Scout";
    scout.missiles_fired = 5;
    scout.missiles_landed = 2;
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("missile_accuracy_string", scout),
        "");

    // Dummy totals player should return missile accuracy string
    PlayerSnapshot dummy;
    dummy.is_dummy = true;
    dummy.missiles_fired = 20;
    dummy.missiles_landed = 8;
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("missile_accuracy_string", dummy),
        "8/20");

    // Custom placeholders test
    std::string template_str =
        "Hits: {medic_hits} | Shots: {shots_landed}/{shots_fired} ({accuracy}) "
        "| Nukes: {nukes_activated}/{nukes_detonated} "
        "| Missiles: {missiles_landed}/{missiles_fired}";
    EXPECT_EQ(
        TextComponent::ResolvePlayerText("custom", p, template_str),
        "Hits: 10/3/-2 | Shots: 100/400 (25.0%) "
        "| Nukes: 2/1 | Missiles: 4/10");
}

TEST(TextComponentTest, PlayerStateColorsAndRapidFire) {
    ElementConfig el;
    el.type = "player_name";
    el.font_size = 20.0f;

    // 1. Alive player
    PlayerSnapshot p_alive;
    p_alive.name = "Warrior";
    p_alive.state = 0; // Up
    p_alive.lives = 5;
    p_alive.has_rapid_fire = true;

    RenderBatch b1;
    TextComponent::GeneratePlayerElementCommands(
        el, p_alive, "#ff0000", {0.0f, 0.0f, 200.0f, 30.0f}, 800.0f, b1);
    ASSERT_EQ(b1.commands.size(), 1u);
    EXPECT_EQ(b1.commands[0].hex_color, "#ff0000");
    EXPECT_TRUE(b1.commands[0].rapid_fire_effect);

    // 2. Dead player (state 4 or out of lives) -> gray
    PlayerSnapshot p_dead;
    p_dead.name = "Ghost";
    p_dead.state = 4;
    p_dead.lives = 0;
    p_dead.has_rapid_fire = false;

    RenderBatch b2;
    TextComponent::GeneratePlayerElementCommands(
        el, p_dead, "#ff0000", {0.0f, 0.0f, 200.0f, 30.0f}, 800.0f, b2);
    ASSERT_EQ(b2.commands.size(), 1u);
    EXPECT_EQ(b2.commands[0].hex_color, "#808080");
    EXPECT_FALSE(b2.commands[0].rapid_fire_effect);

    // 3. Down player (state 3) -> darkened color, no rapid fire even if active
    PlayerSnapshot p_down;
    p_down.name = "Downed";
    p_down.state = 3;
    p_down.lives = 3;
    p_down.has_rapid_fire = true;

    RenderBatch b3;
    TextComponent::GeneratePlayerElementCommands(
        el, p_down, "#ff0000", {0.0f, 0.0f, 200.0f, 30.0f}, 800.0f, b3);
    ASSERT_EQ(b3.commands.size(), 1u);
    EXPECT_EQ(b3.commands[0].hex_color, "#7f0000"); // Darkened #ff0000
    EXPECT_FALSE(b3.commands[0].rapid_fire_effect);

    // 4. Resettable player (state 2) -> no rapid fire even if active
    PlayerSnapshot p_resettable;
    p_resettable.name = "Reset";
    p_resettable.state = 2;
    p_resettable.lives = 2;
    p_resettable.has_rapid_fire = true;

    RenderBatch b4;
    TextComponent::GeneratePlayerElementCommands(
        el, p_resettable, "#ff0000", {0.0f, 0.0f, 200.0f, 30.0f}, 800.0f, b4);
    ASSERT_EQ(b4.commands.size(), 1u);
    EXPECT_FALSE(b4.commands[0].rapid_fire_effect);

    // 5. Dead player (state 4) with rapid fire -> no rapid fire effect
    PlayerSnapshot p_dead_rf;
    p_dead_rf.name = "DeadRF";
    p_dead_rf.state = 4;
    p_dead_rf.lives = 0;
    p_dead_rf.has_rapid_fire = true;

    RenderBatch b5;
    TextComponent::GeneratePlayerElementCommands(
        el, p_dead_rf, "#ff0000", {0.0f, 0.0f, 200.0f, 30.0f}, 800.0f, b5);
    ASSERT_EQ(b5.commands.size(), 1u);
    EXPECT_FALSE(b5.commands[0].rapid_fire_effect);
}

TEST(TextComponentTest, RichTextMarkupMultiRunLayout) {
    ElementConfig el;
    el.type = "user_text";
    el.font_size = 20.0f;
    el.alignment = "center";

    // Text with markup
    std::string markup = "<font color=\"#ff0000\">RED</font> vs <font color=\"#00ff00\">GREEN</font>";

    RenderBatch batch;
    TextComponent::GenerateCommands(
        el, markup, {100.0f, 50.0f, 500.0f, 40.0f}, "#ffffff", false, 800.0f, batch);

    ASSERT_EQ(batch.commands.size(), 3u);

    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[0].text, "RED");
    EXPECT_EQ(batch.commands[0].hex_color, "#ff0000");

    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[1].text, " vs ");
    EXPECT_EQ(batch.commands[1].hex_color, "#ffffff");

    EXPECT_EQ(batch.commands[2].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[2].text, "GREEN");
    EXPECT_EQ(batch.commands[2].hex_color, "#00ff00");

    // Centered layout should place runs sequentially with start x > 100.0f
    EXPECT_GT(batch.commands[0].pixel_rect[0], 100.0f);
    EXPECT_GT(batch.commands[1].pixel_rect[0], batch.commands[0].pixel_rect[0]);
    EXPECT_GT(batch.commands[2].pixel_rect[0], batch.commands[1].pixel_rect[0]);
}

TEST(TextComponentTest, InlineImageRunInText) {
    ElementConfig el;
    el.type = "user_text";
    el.font_size = 20.0f;
    el.alignment = "left";

    std::string text_with_img = "Star [img:assets/star.png] Rank";

    RenderBatch batch;
    TextComponent::GenerateCommands(
        el, text_with_img, {0.0f, 0.0f, 400.0f, 40.0f}, "#ffffff", false, 800.0f, batch);

    ASSERT_EQ(batch.commands.size(), 3u);

    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[0].text, "Star ");

    EXPECT_EQ(batch.commands[1].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[1].texture_asset, "assets/star.png");

    EXPECT_EQ(batch.commands[2].type, RenderCommand::Type::Text);
    EXPECT_EQ(batch.commands[2].text, " Rank");
}

TEST(TextComponentTest, PlayerRoleVisualizesAsImageInSM5) {
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("Commander"),
        "assets/sm5/commander.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("heavy"),
        "assets/sm5/heavy.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("Scout"),
        "assets/sm5/scout.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("Medic"),
        "assets/sm5/medic.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("Ammo Carrier"),
        "assets/sm5/ammo.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset("ammo"),
        "assets/sm5/ammo.png");
    EXPECT_EQ(
        TextComponent::GetRoleImageAsset(""),
        "assets/sm5/commander.png");

    ElementConfig el;
    el.type = "player_role";
    el.font_size = 20.0f;
    el.opacity = 0.95f;

    PlayerSnapshot p;
    p.role = "heavy";
    p.lives = 3;
    p.state = 0;

    RenderBatch batch;
    TextComponent::GeneratePlayerElementCommands(
        el, p, "#FF5000", {50.0f, 100.0f, 60.0f, 30.0f}, 720.0f, batch);

    ASSERT_EQ(batch.commands.size(), 1u);
    EXPECT_EQ(batch.commands[0].type, RenderCommand::Type::TexturedQuad);
    EXPECT_EQ(batch.commands[0].texture_asset, "assets/sm5/heavy.png");
    EXPECT_FLOAT_EQ(batch.commands[0].opacity, 0.95f);
    // At 720p height, font size 20 is 18px
    EXPECT_FLOAT_EQ(batch.commands[0].pixel_rect[2], 18.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].pixel_rect[3], 18.0f);
    // Active player is tinted with team color
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[0], 1.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[1], 80.0f / 255.0f);
    EXPECT_FLOAT_EQ(batch.commands[0].color_rgba[2], 0.0f);
}

TEST(TextComponentTest, PlayerRoleTintMatchesPlayerState) {
    ElementConfig el;
    el.type = "player_role";
    el.font_size = 20.0f;

    // 1. Down player (state 3) -> darkened team color
    PlayerSnapshot down_p;
    down_p.role = "medic";
    down_p.lives = 2;
    down_p.state = 3;

    RenderBatch batch_down;
    TextComponent::GeneratePlayerElementCommands(
        el, down_p, "#00FF00", {0.0f, 0.0f, 100.0f, 30.0f}, 800.0f,
        batch_down);
    ASSERT_EQ(batch_down.commands.size(), 1u);
    EXPECT_FLOAT_EQ(batch_down.commands[0].pixel_rect[2], 20.0f);
    EXPECT_FLOAT_EQ(batch_down.commands[0].pixel_rect[3], 20.0f);
    EXPECT_FLOAT_EQ(batch_down.commands[0].color_rgba[0], 0.0f);
    EXPECT_FLOAT_EQ(batch_down.commands[0].color_rgba[1], 127.0f / 255.0f);
    EXPECT_FLOAT_EQ(batch_down.commands[0].color_rgba[2], 0.0f);

    // 2. Dead player (lives 0 or state 4) -> gray #808080
    PlayerSnapshot dead_p;
    dead_p.role = "scout";
    dead_p.lives = 0;
    dead_p.state = 4;

    RenderBatch batch_dead;
    TextComponent::GeneratePlayerElementCommands(
        el, dead_p, "#00FF00", {0.0f, 0.0f, 100.0f, 30.0f}, 800.0f,
        batch_dead);
    ASSERT_EQ(batch_dead.commands.size(), 1u);
    EXPECT_FLOAT_EQ(batch_dead.commands[0].color_rgba[0], 128.0f / 255.0f);
    EXPECT_FLOAT_EQ(batch_dead.commands[0].color_rgba[1], 128.0f / 255.0f);
    EXPECT_FLOAT_EQ(batch_dead.commands[0].color_rgba[2], 128.0f / 255.0f);
}

TEST(TextComponentTest, MultilineTextWithVerticalSpacing) {
    ElementConfig el;
    el.type = "user_text";
    el.font_size = 20.0f;
    el.vertical_spacing = 5.0f;

    RenderBatch batch;
    TextComponent::GenerateCommands(
        el,
        "Line 1\nLine 2\nLine 3",
        {10.0f, 100.0f, 200.0f, 100.0f},
        "#ffffff",
        false,
        800.0f,
        batch);

    ASSERT_EQ(batch.commands.size(), 3u);
    EXPECT_EQ(batch.commands[0].text, "Line 1");
    EXPECT_EQ(batch.commands[1].text, "Line 2");
    EXPECT_EQ(batch.commands[2].text, "Line 3");

    EXPECT_FLOAT_EQ(batch.commands[0].pixel_rect[1], 100.0f);
    EXPECT_FLOAT_EQ(batch.commands[1].pixel_rect[1], 125.0f);
    EXPECT_FLOAT_EQ(batch.commands[2].pixel_rect[1], 150.0f);
}

TEST(TextComponentTest,
     MultilineTextWithVerticalSpacingScalesWithWindowHeight) {
    ElementConfig el;
    el.type = "user_text";
    el.font_size = 20.0f;
    el.vertical_spacing = 5.0f;

    RenderBatch batch;
    TextComponent::GenerateCommands(
        el,
        "Line 1\nLine 2\nLine 3",
        {10.0f, 100.0f, 200.0f, 100.0f},
        "#ffffff",
        false,
        1600.0f,
        batch);

    ASSERT_EQ(batch.commands.size(), 3u);
    EXPECT_EQ(batch.commands[0].text, "Line 1");
    EXPECT_EQ(batch.commands[1].text, "Line 2");
    EXPECT_EQ(batch.commands[2].text, "Line 3");

    // At 1600px window height:
    // font_size_px = 40.0f, scaled vertical_spacing = 10.0f
    // step_y = 40.0f + 10.0f = 50.0f
    EXPECT_FLOAT_EQ(batch.commands[0].pixel_rect[1], 100.0f);
    EXPECT_FLOAT_EQ(batch.commands[1].pixel_rect[1], 150.0f);
    EXPECT_FLOAT_EQ(batch.commands[2].pixel_rect[1], 200.0f);
}

TEST(TextComponentTest, MultiRunSegmentsAlignWithFontMetrics) {
    ElementConfig el;
    el.type = "user_text";
    el.font = "Anton-Regular";
    el.font_size = 20.0f;
    el.alignment = "left";

    std::string msg =
        "<font color=\"#ff0000\">PlayerA</font> zaps "
        "<font color=\"#0000ff\">PlayerB</font>";

    RenderBatch batch;
    TextComponent::GenerateCommands(
        el,
        msg,
        {50.0f, 100.0f, 600.0f, 30.0f},
        "#ffffff",
        false,
        800.0f,
        batch);

    ASSERT_EQ(batch.commands.size(), 3u);
    EXPECT_EQ(batch.commands[0].text, "PlayerA");
    EXPECT_EQ(batch.commands[1].text, " zaps ");
    EXPECT_EQ(batch.commands[2].text, "PlayerB");

    float w_playera = FontRenderer::MeasureText(
        "PlayerA", "Anton-Regular", 20.0f);
    float w_zaps = FontRenderer::MeasureText(
        " zaps ", "Anton-Regular", 20.0f);

    EXPECT_GT(w_playera, 0.0f);
    EXPECT_GT(w_zaps, 0.0f);

    EXPECT_FLOAT_EQ(batch.commands[0].pixel_rect[0], 50.0f);
    EXPECT_FLOAT_EQ(batch.commands[1].pixel_rect[0], 50.0f + w_playera);
    EXPECT_FLOAT_EQ(
        batch.commands[2].pixel_rect[0], 50.0f + w_playera + w_zaps);
}


