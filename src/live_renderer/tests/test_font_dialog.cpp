#include <gtest/gtest.h>
#include "live_renderer/widgets/font_dialog.hpp"

using namespace live_renderer;

TEST(FontDialogTest, PlatformSupportCheck) {
#if defined(_WIN32)
    EXPECT_TRUE(FontDialog::IsSupported());
#else
    EXPECT_FALSE(FontDialog::IsSupported());
    EXPECT_TRUE(FontDialog::ShowFontDialog("Arial").empty());
#endif
}

