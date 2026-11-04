#include <gtest/gtest.h>
#include "live_renderer/render/render_geometry.hpp"

using namespace live_renderer;

TEST(RenderGeometryTest, HandlesDegenerateDimensionsSafely) {
    // Should return early safely with zero or negative dimensions
    EXPECT_NO_THROW(
        RenderGeometry::DrawSolidQuad(
            {0.0f, 0.0f, 0.0f, 100.0f},
            {1.0f, 1.0f, 1.0f, 1.0f},
            5.0f));

    EXPECT_NO_THROW(
        RenderGeometry::DrawSolidQuad(
            {10.0f, 10.0f, -50.0f, 100.0f},
            {1.0f, 0.0f, 0.0f, 1.0f},
            0.0f));

    EXPECT_NO_THROW(
        RenderGeometry::DrawTexturedQuad(
            {0.0f, 0.0f, 100.0f, 0.0f},
            {0.0f, 0.0f, 1.0f, 1.0f},
            10.0f));
}

TEST(RenderGeometryTest, ValidDimensionsExecuteWithoutCrash) {
    // Sharp corners (radius 0)
    EXPECT_NO_THROW(
        RenderGeometry::DrawSolidQuad(
            {10.0f, 20.0f, 200.0f, 100.0f},
            {0.2f, 0.3f, 0.4f, 1.0f},
            0.0f));

    // Rounded corners (radius 15)
    EXPECT_NO_THROW(
        RenderGeometry::DrawSolidQuad(
            {10.0f, 20.0f, 200.0f, 100.0f},
            {0.5f, 0.6f, 0.7f, 0.8f},
            15.0f));

    // Clamped corner radius (radius larger than half height)
    EXPECT_NO_THROW(
        RenderGeometry::DrawSolidQuad(
            {10.0f, 20.0f, 200.0f, 50.0f},
            {1.0f, 1.0f, 1.0f, 1.0f},
            80.0f));

    // Textured quad with sharp corners
    EXPECT_NO_THROW(
        RenderGeometry::DrawTexturedQuad(
            {0.0f, 0.0f, 150.0f, 80.0f},
            {0.0f, 0.0f, 1.0f, 1.0f},
            0.0f));

    // Textured quad with rounded corners
    EXPECT_NO_THROW(
        RenderGeometry::DrawTexturedQuad(
            {0.0f, 0.0f, 150.0f, 80.0f},
            {0.1f, 0.1f, 0.9f, 0.9f},
            12.0f));
}

