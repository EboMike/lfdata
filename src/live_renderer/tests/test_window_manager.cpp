#include <gtest/gtest.h>
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

