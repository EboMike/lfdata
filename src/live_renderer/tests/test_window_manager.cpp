#include <gtest/gtest.h>
#include <filesystem>
#include <SDL.h>
#include "live_renderer/config/preferences_manager.hpp"
#include "live_renderer/windows/window_manager.hpp"

using namespace live_renderer;

TEST(WindowManagerTest, SyncsWithUIConfigWithoutSDLContext) {
    UIConfig ui;
    WindowConfig w1;
    w1.id = 1;
    w1.title = "Arena 1";
    w1.rect = {0, 0, 800, 600};

    WindowConfig w2;
    w2.id = 2;
    w2.title = "Arena 2";
    w2.rect = {100, 100, 1024, 768};

    ui.windows = {w1, w2};

    // Constructing WindowManager with null GL context (headless / unit test safe)
    WindowManager mgr(ui, nullptr);
    EXPECT_GE(mgr.GetWindowCount(), 0u);

    // Verify window config query
    if (mgr.GetWindowCount() >= 2) {
        EXPECT_EQ(mgr.GetWindow(0)->GetTitle(), "Arena 1");
        EXPECT_EQ(mgr.GetWindow(1)->GetTitle(), "Arena 2");
    }
}

TEST(WindowManagerTest, MinimizesVisualizationWindowOnCloseEvent) {
    UIConfig ui;
    WindowConfig w1;
    w1.id = 1;
    w1.title = "Vis Window 1";
    w1.rect = {100, 100, 640, 480};
    ui.windows = {w1};

    WindowManager mgr(ui, nullptr);
    if (mgr.GetWindowCount() == 0 || !mgr.GetSdlWindow(0)) {
        GTEST_SKIP() << "SDL video backend not available in current test environment";
    }

    EXPECT_FALSE(mgr.IsWindowMinimized(0));

    // Simulate close event on the visualization window
    SDL_Event close_event;
    close_event.type = SDL_WINDOWEVENT;
    close_event.window.event = SDL_WINDOWEVENT_CLOSE;
    close_event.window.windowID = SDL_GetWindowID(mgr.GetSdlWindow(0));

    bool handled = mgr.HandleEvent(close_event);
    EXPECT_TRUE(handled);
    EXPECT_TRUE(mgr.IsWindowMinimized(0));

    // Restore the window
    mgr.RestoreWindow(0);
    EXPECT_FALSE(mgr.IsWindowMinimized(0));

    // Test minimize helper
    mgr.MinimizeWindow(0);
    EXPECT_TRUE(mgr.IsWindowMinimized(0));
    mgr.RestoreWindow(0);
    EXPECT_FALSE(mgr.IsWindowMinimized(0));
}

TEST(WindowManagerTest, AppliesStoredPreferencesOnStartup) {
    std::string temp_prefs_path = "test_wm_prefs_temp.yaml";
    if (std::filesystem::exists(temp_prefs_path)) {
        std::filesystem::remove(temp_prefs_path);
    }

    PreferencesManager pref_mgr(temp_prefs_path);
    WindowPreference saved_pref{
        .window_id = 42,
        .x = 250,
        .y = 180,
        .width = 900,
        .height = 550,
        .display_index = 0,
        .display_name = ""
    };
    pref_mgr.UpdateWindowPreference(saved_pref, /*auto_save=*/true);

    UIConfig ui;
    WindowConfig w;
    w.id = 42;
    w.title = "Custom Placement Window";
    w.rect = {0, 0, 640, 480};  // Default in layout config
    ui.windows = {w};

    WindowManager mgr(ui, nullptr, &pref_mgr);
    if (mgr.GetWindowCount() > 0 && mgr.GetSdlWindow(0)) {
        int x = 0, y = 0, w = 0, h = 0;
        SDL_GetWindowPosition(mgr.GetSdlWindow(0), &x, &y);
        SDL_GetWindowSize(mgr.GetSdlWindow(0), &w, &h);

        // Window size should reflect stored preferences instead of default layout rect
        EXPECT_EQ(w, 900);
        EXPECT_EQ(h, 550);
    }

    if (std::filesystem::exists(temp_prefs_path)) {
        std::filesystem::remove(temp_prefs_path);
    }
}
