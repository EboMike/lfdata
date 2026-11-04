#include <gtest/gtest.h>
#include "live_renderer/config/config_serializer.hpp"
#include <filesystem>

using namespace live_renderer;

TEST(ConfigSerializerTest, RoundTripGlobalConfig) {
    GlobalConfig cfg;
    cfg.host = "192.168.1.50";
    cfg.port = 8888;
    cfg.ui_config_file = "custom_layout.yaml";

    std::string path = "test_global_config.yaml";
    EXPECT_TRUE(ConfigSerializer::SaveGlobalConfig(path, cfg));

    GlobalConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadGlobalConfig(path, loaded));
    EXPECT_EQ(loaded.host, "192.168.1.50");
    EXPECT_EQ(loaded.port, 8888);
    EXPECT_EQ(loaded.ui_config_file, "custom_layout.yaml");

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
    scorecard.change_animation = "ease-in-and-ease-out";
    scorecard.animation_duration = 0.75f;
    win.elements.push_back(scorecard);

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
    ASSERT_EQ(loaded.windows[0].elements.size(), 2);
    EXPECT_EQ(loaded.windows[0].elements[0].type, "game_timer");
    EXPECT_EQ(loaded.windows[0].elements[1].type, "team_scorecard");
    EXPECT_EQ(
        loaded.windows[0].elements[1].change_animation,
        "ease-in-and-ease-out");
    EXPECT_FLOAT_EQ(
        loaded.windows[0].elements[1].animation_duration, 0.75f);

    std::filesystem::remove(path);
}

