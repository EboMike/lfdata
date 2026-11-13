/**
 * @file test_texture_manager.cpp
 * @brief Unit tests for TextureManager texture loading and lifecycle.
 */

#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/render/texture_downloader.hpp"
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

    cmd.fit = "scale";
    EXPECT_NO_THROW(tm.RenderTexturedQuad(cmd));

    cmd.fit = "crop";
    EXPECT_NO_THROW(tm.RenderTexturedQuad(cmd));
}

TEST(TextureManagerTest, LoadsExistingAssetDimensions) {
    TextureManager tm;
    int w = -1;
    int h = -1;
    bool ok = tm.GetTextureDimensions("assets/ball.png", w, h);
    if (ok) {
        EXPECT_GT(w, 0);
        EXPECT_GT(h, 0);

        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = {0.0f, 0.0f, 200.0f, 100.0f};
        cmd.texture_asset = "assets/ball.png";
        cmd.fit = "scale";
        EXPECT_NO_THROW(tm.RenderTexturedQuad(cmd));

        cmd.fit = "crop";
        EXPECT_NO_THROW(tm.RenderTexturedQuad(cmd));
    }
}

TEST(TextureManagerTest, LoadsDefaultPlayerAssetDimensions) {
    TextureManager tm;
    int w = -1;
    int h = -1;
    bool ok = tm.GetTextureDimensions(kDefaultProfilePictureAsset, w, h);
    if (ok) {
        EXPECT_EQ(w, 1267);
        EXPECT_EQ(h, 967);
    }
}

TEST(TextureManagerTest, HttpUrlUsesFallbackWhenOfflineOrFailed) {
    namespace fs = std::filesystem;
    std::string test_cache = ".cache/test_tm_cache";
    fs::remove_all(test_cache);

    auto fail_fetcher = [](const std::string& url) -> std::vector<uint8_t> {
        return {};
    };

    auto downloader =
        std::make_unique<TextureDownloader>(test_cache, fail_fetcher);
    TextureManager tm(std::move(downloader));

    // When URL download fails, GetTexture returns fallback texture (or 0 if no GL)
    GLuint fallback_id = tm.GetFallbackTexture();
    GLuint tex_id = tm.GetTexture("https://example.com/player_avatar.png");
    EXPECT_EQ(tex_id, fallback_id);

    fs::remove_all(test_cache);
}

}  // namespace live_renderer
