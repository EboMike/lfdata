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

    // Test with rapid fire enabled
    cmd.rapid_fire_effect = true;
    EXPECT_NO_THROW(renderer.RenderText(cmd, 1000));
}

TEST(FontRendererTest, RapidFireBrighteningGradientMovesRight) {
    const float base_color[4] = {0.2f, 0.4f, 0.6f, 1.0f};
    float c0[4]{};
    float c1[4]{};

    // At t=0 ms, compute at px=0
    FontRenderer::ComputeBrightenedColor(base_color, 0.0f, 0, c0);
    // At t=0 ms, compute at peak (35px into band)
    FontRenderer::ComputeBrightenedColor(base_color, 35.0f, 0, c1);

    // Peak should be noticeably brighter than base
    EXPECT_GT(c1[0], c0[0]);
    EXPECT_GT(c1[1], c0[1]);
    EXPECT_GT(c1[2], c0[2]);
    EXPECT_FLOAT_EQ(c1[3], base_color[3]);  // Alpha preserved

    // Wave moves right with speed 0.15 px/ms.
    // In 200 ms, wave moves by 30 px.
    // The peak should move from 35 px to 65 px.
    float c_wave_t200[4]{};
    FontRenderer::ComputeBrightenedColor(base_color, 65.0f, 200, c_wave_t200);
    EXPECT_NEAR(c_wave_t200[0], c1[0], 0.01f);
    EXPECT_NEAR(c_wave_t200[1], c1[1], 0.01f);
    EXPECT_NEAR(c_wave_t200[2], c1[2], 0.01f);
}

}  // namespace live_renderer

