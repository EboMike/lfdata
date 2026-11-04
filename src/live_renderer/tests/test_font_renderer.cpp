/**
 * @file test_font_renderer.cpp
 * @brief Unit tests for FontRenderer font resolution, layout, and rendering.
 */

#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/render/font_renderer.hpp"

namespace live_renderer {

TEST(FontRendererTest, ResolveFontPathEmptyOrDefault) {
    EXPECT_TRUE(FontRenderer::ResolveFontPath("").empty());
    EXPECT_TRUE(FontRenderer::ResolveFontPath("default").empty());
}

TEST(FontRendererTest, ResolveFontPathProjectFonts) {
    // Project fonts directory check
    std::string path_anton = FontRenderer::ResolveFontPath("Anton-Regular");
    if (!path_anton.empty()) {
        EXPECT_TRUE(std::filesystem::exists(path_anton));
    }

    std::string path_google = FontRenderer::ResolveFontPath("GoogleSans-Bold");
    if (!path_google.empty()) {
        EXPECT_TRUE(std::filesystem::exists(path_google));
    }
}

TEST(FontRendererTest, ResolveFontPathSystemFontsOnWindows) {
#if defined(_WIN32)
    std::string path_arial = FontRenderer::ResolveFontPath("Arial");
    if (!path_arial.empty()) {
        EXPECT_TRUE(std::filesystem::exists(path_arial));
    }

    std::string path_consolas = FontRenderer::ResolveFontPath("Consolas");
    if (!path_consolas.empty()) {
        EXPECT_TRUE(std::filesystem::exists(path_consolas));
    }
#endif
}

TEST(FontRendererTest, ResolveFontPathNonExistent) {
    EXPECT_TRUE(FontRenderer::ResolveFontPath(
        "NonExistentFontFamily_XYZ_12345").empty());
}

TEST(FontRendererTest, DefaultFontGetAndSet) {
    FontRenderer renderer;
    EXPECT_EQ(renderer.GetDefaultFont(), "default");

    renderer.SetDefaultFont("Arial");
    EXPECT_EQ(renderer.GetDefaultFont(), "Arial");

    renderer.SetDefaultFont("Consolas");
    EXPECT_EQ(renderer.GetDefaultFont(), "Consolas");
}

TEST(FontRendererTest, MeasureTextWidthCalculations) {
    FontRenderer renderer;

    EXPECT_FLOAT_EQ(renderer.MeasureTextWidth("", "default", 20.0f), 0.0f);

    float w_short = renderer.MeasureTextWidth("AB", "default", 20.0f);
    float w_long = renderer.MeasureTextWidth("ABCD", "default", 20.0f);
    EXPECT_GT(w_short, 0.0f);
    EXPECT_GT(w_long, w_short);

    // Font scaling
    float w_large = renderer.MeasureTextWidth("AB", "default", 40.0f);
    EXPECT_GT(w_large, w_short);
}

TEST(FontRendererTest, RenderCommandWithoutContextDoesNotCrash) {
    FontRenderer renderer;
    RenderCommand cmd;
    cmd.type = RenderCommand::Type::Text;
    cmd.text = "Testing Font";
    cmd.font = "default";
    cmd.pixel_rect = {10.0f, 10.0f, 200.0f, 40.0f};
    cmd.font_size_px = 24.0f;
    cmd.hex_color = "#ff8800";
    cmd.alignment = "center";
    cmd.black_outline = true;

    // Should handle execution gracefully
    EXPECT_NO_THROW(renderer.RenderText(cmd));
}

}  // namespace live_renderer

