#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/config/preferences_manager.hpp"

using namespace live_renderer;

class PreferencesManagerTest : public ::testing::Test {
protected:
    void SetUp() override {
        test_pref_path_ = "test_preferences_temp.yaml";
        if (std::filesystem::exists(test_pref_path_)) {
            std::filesystem::remove(test_pref_path_);
        }
    }

    void TearDown() override {
        if (std::filesystem::exists(test_pref_path_)) {
            std::filesystem::remove(test_pref_path_);
        }
    }

    std::string test_pref_path_;
};

TEST_F(PreferencesManagerTest, RoundTripSerialization) {
    LocalPreferences orig;
    WindowPreference main_win{
        .window_id = 0,
        .x = 200,
        .y = 150,
        .width = 450,
        .height = 300,
        .display_index = 0,
        .display_name = "\\\\.\\DISPLAY1"
    };
    orig.main_control_window = main_win;

    WindowPreference w1{
        .window_id = 1,
        .x = 100,
        .y = 120,
        .width = 1280,
        .height = 720,
        .display_index = 0,
        .display_name = "\\\\.\\DISPLAY1"
    };
    WindowPreference w2{
        .window_id = 2,
        .x = 1920,
        .y = 50,
        .width = 1920,
        .height = 1080,
        .display_index = 1,
        .display_name = "\\\\.\\DISPLAY2"
    };
    orig.windows = {w1, w2};

    EXPECT_TRUE(ConfigSerializer::SavePreferences(test_pref_path_, orig));

    LocalPreferences loaded;
    EXPECT_TRUE(ConfigSerializer::LoadPreferences(test_pref_path_, loaded));

    ASSERT_TRUE(loaded.main_control_window.has_value());
    EXPECT_EQ(loaded.main_control_window->x, 200);
    EXPECT_EQ(loaded.main_control_window->y, 150);
    EXPECT_EQ(loaded.main_control_window->width, 450);
    EXPECT_EQ(loaded.main_control_window->height, 300);
    EXPECT_EQ(loaded.main_control_window->display_index, 0);
    EXPECT_EQ(loaded.main_control_window->display_name, "\\\\.\\DISPLAY1");

    ASSERT_EQ(loaded.windows.size(), 2u);
    EXPECT_EQ(loaded.windows[0].window_id, 1);
    EXPECT_EQ(loaded.windows[0].x, 100);
    EXPECT_EQ(loaded.windows[0].y, 120);
    EXPECT_EQ(loaded.windows[0].width, 1280);
    EXPECT_EQ(loaded.windows[0].height, 720);
    EXPECT_EQ(loaded.windows[0].display_index, 0);
    EXPECT_EQ(loaded.windows[0].display_name, "\\\\.\\DISPLAY1");

    EXPECT_EQ(loaded.windows[1].window_id, 2);
    EXPECT_EQ(loaded.windows[1].x, 1920);
    EXPECT_EQ(loaded.windows[1].y, 50);
    EXPECT_EQ(loaded.windows[1].width, 1920);
    EXPECT_EQ(loaded.windows[1].height, 1080);
    EXPECT_EQ(loaded.windows[1].display_index, 1);
    EXPECT_EQ(loaded.windows[1].display_name, "\\\\.\\DISPLAY2");
}

TEST_F(PreferencesManagerTest, GetAndUpdateWindowPreference) {
    PreferencesManager mgr(test_pref_path_);

    WindowPreference pref1{
        .window_id = 1,
        .x = 50,
        .y = 60,
        .width = 800,
        .height = 600,
        .display_index = 0,
        .display_name = "Monitor 1"
    };
    mgr.UpdateWindowPreference(pref1, /*auto_save=*/true);

    const auto* retrieved = mgr.GetWindowPreference(1);
    ASSERT_NE(retrieved, nullptr);
    EXPECT_EQ(retrieved->x, 50);
    EXPECT_EQ(retrieved->y, 60);
    EXPECT_EQ(retrieved->width, 800);
    EXPECT_EQ(retrieved->height, 600);
    EXPECT_EQ(retrieved->display_name, "Monitor 1");

    // Updating existing preference modifies in place
    WindowPreference pref1_updated{
        .window_id = 1,
        .x = 200,
        .y = 250,
        .width = 1024,
        .height = 768,
        .display_index = 1,
        .display_name = "Monitor 2"
    };
    mgr.UpdateWindowPreference(pref1_updated, /*auto_save=*/true);

    retrieved = mgr.GetWindowPreference(1);
    ASSERT_NE(retrieved, nullptr);
    EXPECT_EQ(retrieved->x, 200);
    EXPECT_EQ(retrieved->y, 250);
    EXPECT_EQ(retrieved->width, 1024);
    EXPECT_EQ(retrieved->height, 768);
    EXPECT_EQ(retrieved->display_name, "Monitor 2");

    EXPECT_EQ(mgr.GetWindowPreference(999), nullptr);
}

TEST_F(PreferencesManagerTest, GlobalConfigStoresPreferencesFile) {
    std::string config_path = "test_global_config_pref.yaml";
    GlobalConfig cfg;
    cfg.host = "192.168.1.100";
    cfg.port = 9000;
    cfg.ui_config_file = "custom_layout.yaml";
    cfg.preferences_file = "my_custom_preferences.yaml";

    EXPECT_TRUE(ConfigSerializer::SaveGlobalConfig(config_path, cfg));

    GlobalConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadGlobalConfig(config_path, loaded));
    EXPECT_EQ(loaded.preferences_file, "my_custom_preferences.yaml");

    if (std::filesystem::exists(config_path)) {
        std::filesystem::remove(config_path);
    }
}

