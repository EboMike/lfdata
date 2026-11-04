/**
 * @file test_texture_fit.cpp
 * @brief Unit tests for TextureFit calculation helper.
 */

#include <gtest/gtest.h>
#include "live_renderer/render/texture_fit.hpp"

namespace live_renderer {

TEST(TextureFitTest, ParseAndStringConversion) {
    EXPECT_EQ(TextureFit::ParseFitMode("stretch"), TextureFitMode::Stretch);
    EXPECT_EQ(TextureFit::ParseFitMode("Scale"), TextureFitMode::Scale);
    EXPECT_EQ(TextureFit::ParseFitMode("crop"), TextureFitMode::Crop);
    EXPECT_EQ(TextureFit::ParseFitMode("invalid"), TextureFitMode::Stretch);

    EXPECT_EQ(TextureFit::FitModeToString(TextureFitMode::Stretch), "stretch");
    EXPECT_EQ(TextureFit::FitModeToString(TextureFitMode::Scale), "scale");
    EXPECT_EQ(TextureFit::FitModeToString(TextureFitMode::Crop), "crop");
}

TEST(TextureFitTest, HandlesInvalidDimensions) {
    std::array<float, 4> rect{10.0f, 20.0f, 100.0f, 50.0f};
    auto res1 = TextureFit::Compute(rect, 0, 100, TextureFitMode::Scale);
    EXPECT_EQ(res1.pixel_rect, rect);

    auto res2 = TextureFit::Compute(rect, 100, -5, TextureFitMode::Crop);
    EXPECT_EQ(res2.pixel_rect, rect);

    std::array<float, 4> empty_rect{0.0f, 0.0f, 0.0f, 100.0f};
    auto res3 = TextureFit::Compute(empty_rect, 100, 100, "scale");
    EXPECT_EQ(res3.pixel_rect, empty_rect);
}

TEST(TextureFitTest, StretchModeKeepsContainerAndFullUV) {
    std::array<float, 4> rect{10.0f, 20.0f, 200.0f, 100.0f};
    auto res = TextureFit::Compute(rect, 100, 100, TextureFitMode::Stretch);
    EXPECT_FLOAT_EQ(res.pixel_rect[0], 10.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[1], 20.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[2], 200.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[3], 100.0f);

    EXPECT_FLOAT_EQ(res.uv_rect[0], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[1], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[2], 1.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[3], 1.0f);
}

TEST(TextureFitTest, ScaleModePillarboxesWideContainer) {
    // Container 200x100 (aspect 2.0), Texture 100x100 (aspect 1.0)
    std::array<float, 4> rect{0.0f, 0.0f, 200.0f, 100.0f};
    auto res = TextureFit::Compute(rect, 100, 100, "scale");

    // Scaled size should be 100x100, centered horizontally at x = 50
    EXPECT_FLOAT_EQ(res.pixel_rect[0], 50.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[1], 0.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[2], 100.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[3], 100.0f);

    EXPECT_FLOAT_EQ(res.uv_rect[0], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[1], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[2], 1.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[3], 1.0f);
}

TEST(TextureFitTest, ScaleModeLetterboxesTallContainer) {
    // Container 100x200 (aspect 0.5), Texture 100x100 (aspect 1.0)
    std::array<float, 4> rect{10.0f, 20.0f, 100.0f, 200.0f};
    auto res = TextureFit::Compute(rect, 100, 100, "scale");

    // Scaled size should be 100x100, centered vertically at y = 20 + 50 = 70
    EXPECT_FLOAT_EQ(res.pixel_rect[0], 10.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[1], 70.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[2], 100.0f);
    EXPECT_FLOAT_EQ(res.pixel_rect[3], 100.0f);
}

TEST(TextureFitTest, CropModeCropsTopAndBottomInWideContainer) {
    // Container 200x100 (aspect 2.0), Texture 100x100 (aspect 1.0)
    std::array<float, 4> rect{10.0f, 20.0f, 200.0f, 100.0f};
    auto res = TextureFit::Compute(rect, 100, 100, "crop");

    // Pixel rect covers whole container
    EXPECT_EQ(res.pixel_rect, rect);

    // v_fraction = 1.0 / 2.0 = 0.5. Centered: v0 = 0.25, v1 = 0.75
    EXPECT_FLOAT_EQ(res.uv_rect[0], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[1], 0.25f);
    EXPECT_FLOAT_EQ(res.uv_rect[2], 1.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[3], 0.75f);
}

TEST(TextureFitTest, CropModeCropsLeftAndRightInTallContainer) {
    // Container 100x200 (aspect 0.5), Texture 100x100 (aspect 1.0)
    std::array<float, 4> rect{0.0f, 0.0f, 100.0f, 200.0f};
    auto res = TextureFit::Compute(rect, 100, 100, "crop");

    EXPECT_EQ(res.pixel_rect, rect);

    // u_fraction = 0.5 / 1.0 = 0.5. Centered: u0 = 0.25, u1 = 0.75
    EXPECT_FLOAT_EQ(res.uv_rect[0], 0.25f);
    EXPECT_FLOAT_EQ(res.uv_rect[1], 0.0f);
    EXPECT_FLOAT_EQ(res.uv_rect[2], 0.75f);
    EXPECT_FLOAT_EQ(res.uv_rect[3], 1.0f);
}

}  // namespace live_renderer

