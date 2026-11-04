/**
 * @file test_texture_manager.cpp
 * @brief Unit tests for TextureManager texture loading and lifecycle.
 */

#include <gtest/gtest.h>
#include "live_renderer/render/texture_manager.hpp"

namespace live_renderer {

TEST(TextureManagerTest, EmptyOrNonExistentAssetReturnsZero) {
    TextureManager tm;
    EXPECT_EQ(tm.GetTexture(""), 0u);
    EXPECT_EQ(tm.GetTexture("assets/nonexistent_image_12345.png"), 0u);

    int w = -1;
    int h = -1;
    EXPECT_FALSE(tm.GetTextureDimensions(
        "assets/nonexistent_image_12345.png", w, h));
    EXPECT_EQ(w, -1);
    EXPECT_EQ(h, -1);
}

TEST(TextureManagerTest, UnloadAllClearsCacheSafely) {
    TextureManager tm;
    tm.GetTexture("assets/nonexistent.png");
    tm.UnloadAll();
    EXPECT_EQ(tm.GetTexture(""), 0u);
}

TEST(TextureManagerTest, RenderCommandWithoutContextHandlesFallback) {
    TextureManager tm;
    RenderCommand cmd;
    cmd.type = RenderCommand::Type::TexturedQuad;
    cmd.pixel_rect = {10.0f, 20.0f, 100.0f, 50.0f};
    cmd.texture_asset = "assets/nonexistent.png";
    cmd.opacity = 0.8f;
    cmd.tilt_deg = 5.0f;

    // Should handle missing texture without throwing
    EXPECT_NO_THROW(tm.RenderTexturedQuad(cmd));
}

}  // namespace live_renderer

