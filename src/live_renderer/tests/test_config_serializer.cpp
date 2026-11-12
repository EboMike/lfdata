#include <gtest/gtest.h>
#include "live_renderer/config/config_serializer.hpp"
#include <filesystem>

using namespace live_renderer;

TEST(ConfigSerializerTest, RoundTripGlobalConfig) {
    GlobalConfig cfg;
    cfg.host = "192.168.1.50";
    cfg.port = 8888;
    cfg.ui_config_file = "custom_layout.yaml";
    cfg.default_profile_picture_url = "https://custom.example.com/avatar.png";

    std::string path = "test_global_config.yaml";
    EXPECT_TRUE(ConfigSerializer::SaveGlobalConfig(path, cfg));

    GlobalConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadGlobalConfig(path, loaded));
    EXPECT_EQ(loaded.host, "192.168.1.50");
    EXPECT_EQ(loaded.port, 8888);
    EXPECT_EQ(loaded.ui_config_file, "custom_layout.yaml");
    EXPECT_EQ(loaded.default_profile_picture_url, "https://custom.example.com/avatar.png");

    std::filesystem::remove(path);
}

TEST(ConfigSerializerTest, RoundTripUIConfig) {
    UIConfig ui;
    ui.default_font = "Verdana";
    TemplateConfig tmpl;
    tmpl.id = 1;
    tmpl.name = "RowTmpl";
    tmpl.type = "scorecard_row";
    tmpl.size = {1.0f, 0.04f};

    ElementConfig el;
    el.type = "player_name";
    el.font = "arial";
    el.rect = {0.0f, 0.0f, 0.5f, 1.0f};
    el.font_size = 22.0f;
    el.alignment = "left";
    tmpl.elements.push_back(el);
    ui.templates.push_back(tmpl);

    WindowConfig win;
    win.id = 1;
    win.title = "Arena 1";
    win.rect = {50, 50, 1920, 1080};
    win.monitor_id = 1;

    ElementConfig timer;
    timer.type = "game_timer";
    timer.rect = {0.4f, 0.0f, 0.2f, 0.1f};
    timer.font_size = 36.0f;
    win.elements.push_back(timer);

    ElementConfig scorecard;
    scorecard.type = "team_scorecard";
    scorecard.player_change_animation = "linear";
    scorecard.player_animation_duration = 0.4f;
    scorecard.team_change_animation = "ease-in-and-ease-out";
    scorecard.team_animation_duration = 0.8f;
    scorecard.vertical_spacing = 6.0f;
    scorecard.background.enabled = true;
    scorecard.background.color = "#112233";
    scorecard.background.image_file = "assets/bg.png";
    scorecard.background.movie_file = "assets/bg.mp4";
    scorecard.background.fit = "crop";
    scorecard.background.playback_speed = 0.5f;
    scorecard.background.tint_team_color = 0.8f;
    scorecard.background.opacity = 0.9f;
    scorecard.background.corner_radius = 8.0f;
    scorecard.team_background.enabled = true;
    scorecard.team_background.color = "#445566";
    scorecard.team_background.image_file = "assets/team_bg.png";
    scorecard.team_background.fit = "scale";
    scorecard.team_background.tint_team_color = 0.5f;
    scorecard.team_background.opacity = 0.85f;
    scorecard.team_background.corner_radius = 4.0f;
    win.elements.push_back(scorecard);

    ElementConfig msgs;
    msgs.type = "important_game_messages";
    msgs.lines = 5;
    msgs.display_time = 6.0f;
    msgs.fadeout_time = 1.5f;
    win.elements.push_back(msgs);

    ElementConfig img;
    img.type = "user_image";
    img.image_file = "assets/logo.png";
    img.fit = "crop";
    img.tint_team_color = 0.75f;
    win.elements.push_back(img);

    ElementConfig movie;
    movie.type = "movie";
    movie.movie_file = "assets/clip.mp4";
    movie.fit = "scale";
    movie.playback_speed = 1.5f;
    win.elements.push_back(movie);

    ui.windows.push_back(win);

    std::string path = "test_ui_config.yaml";
    EXPECT_TRUE(ConfigSerializer::SaveUIConfig(path, ui));

    UIConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadUIConfig(path, loaded));
    EXPECT_EQ(loaded.default_font, "Verdana");
    ASSERT_EQ(loaded.templates.size(), 1);
    EXPECT_EQ(loaded.templates[0].name, "RowTmpl");
    ASSERT_EQ(loaded.templates[0].elements.size(), 1);
    EXPECT_EQ(loaded.templates[0].elements[0].type, "player_name");
    EXPECT_EQ(loaded.templates[0].elements[0].font, "arial");

    ASSERT_EQ(loaded.windows.size(), 1);
    EXPECT_EQ(loaded.windows[0].title, "Arena 1");
    EXPECT_EQ(loaded.windows[0].rect[2], 1920);
    ASSERT_EQ(loaded.windows[0].elements.size(), 5);
    EXPECT_EQ(loaded.windows[0].elements[0].type, "game_timer");
    EXPECT_EQ(loaded.windows[0].elements[1].type, "team_scorecard");
    EXPECT_EQ(
        loaded.windows[0].elements[1].player_change_animation,
        "linear");
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].player_animation_duration, 0.4f);
    EXPECT_EQ(
        loaded.windows[0].elements[1].team_change_animation,
        "ease-in-and-ease-out");
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].team_animation_duration, 0.8f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].vertical_spacing, 6.0f);
    EXPECT_TRUE(loaded.windows[0].elements[1].background.enabled);
    EXPECT_EQ(loaded.windows[0].elements[1].background.color, "#112233");
    EXPECT_EQ(
        loaded.windows[0].elements[1].background.image_file, "assets/bg.png");
    EXPECT_EQ(
        loaded.windows[0].elements[1].background.movie_file, "assets/bg.mp4");
    EXPECT_EQ(loaded.windows[0].elements[1].background.fit, "crop");
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].background.playback_speed, 0.5f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].background.tint_team_color, 0.8f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].background.opacity, 0.9f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].background.corner_radius, 8.0f);
    EXPECT_TRUE(loaded.windows[0].elements[1].team_background.enabled);
    EXPECT_EQ(loaded.windows[0].elements[1].team_background.color, "#445566");
    EXPECT_EQ(
        loaded.windows[0].elements[1].team_background.image_file,
        "assets/team_bg.png");
    EXPECT_EQ(loaded.windows[0].elements[1].team_background.fit, "scale");
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].team_background.tint_team_color, 0.5f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].team_background.opacity, 0.85f);
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].team_background.corner_radius, 4.0f);
    EXPECT_EQ(loaded.windows[0].elements[2].type, "important_game_messages");
    EXPECT_EQ(loaded.windows[0].elements[2].lines, 5);
    EXPECT_FLOAT_EQ(loaded.windows[0].elements[2].display_time, 6.0f);
    EXPECT_FLOAT_EQ(loaded.windows[0].elements[2].fadeout_time, 1.5f);

    EXPECT_EQ(loaded.windows[0].elements[3].type, "user_image");
    EXPECT_EQ(loaded.windows[0].elements[3].image_file, "assets/logo.png");
    EXPECT_EQ(loaded.windows[0].elements[3].fit, "crop");
    EXPECT_FLOAT_EQ(loaded.windows[0].elements[3].tint_team_color, 0.75f);

    EXPECT_EQ(loaded.windows[0].elements[4].type, "movie");
    EXPECT_EQ(loaded.windows[0].elements[4].movie_file, "assets/clip.mp4");
    EXPECT_EQ(loaded.windows[0].elements[4].fit, "scale");
    EXPECT_FLOAT_EQ(loaded.windows[0].elements[4].playback_speed, 1.5f);

    std::filesystem::remove(path);
}

TEST(ConfigSerializerTest, RoundTripPaddingAndMargin) {
    UIConfig ui;
    WindowConfig win;
    win.id = 1;
    win.title = "Test Insets";
    win.rect = {0, 0, 1280, 720};

    ElementConfig el;
    el.type = "user_text";
    el.text = "Hello World";
    el.rect = {0.1f, 0.2f, 0.3f, 0.4f};
    el.padding = {0.01f, 0.02f, 0.03f, 0.04f};
    el.margin = {0.05f, 0.06f, 0.07f, 0.08f};
    win.elements.push_back(el);
    ui.windows.push_back(win);

    std::string path = "test_insets_config.yaml";
    EXPECT_TRUE(ConfigSerializer::SaveUIConfig(path, ui));

    UIConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadUIConfig(path, loaded));
    ASSERT_EQ(loaded.windows.size(), 1);
    ASSERT_EQ(loaded.windows[0].elements.size(), 1);
    const auto& loaded_el = loaded.windows[0].elements[0];
    EXPECT_FLOAT_EQ(loaded_el.padding.left, 0.01f);
    EXPECT_FLOAT_EQ(loaded_el.padding.right, 0.02f);
    EXPECT_FLOAT_EQ(loaded_el.padding.up, 0.03f);
    EXPECT_FLOAT_EQ(loaded_el.padding.down, 0.04f);
    EXPECT_FLOAT_EQ(loaded_el.margin.left, 0.05f);
    EXPECT_FLOAT_EQ(loaded_el.margin.right, 0.06f);
    EXPECT_FLOAT_EQ(loaded_el.margin.up, 0.07f);
    EXPECT_FLOAT_EQ(loaded_el.margin.down, 0.08f);

    std::filesystem::remove(path);
}


