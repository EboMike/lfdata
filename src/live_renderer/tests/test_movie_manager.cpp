/**
 * @file test_movie_manager.cpp
 * @brief Unit tests for MovieManager looped playback and frame tracking.
 */

#include <filesystem>
#include <gtest/gtest.h>
#include "live_renderer/render/movie_manager.hpp"

namespace live_renderer {

TEST(MovieManagerTest, EmptyOrNonExistentMovieReturnsZero) {
    MovieManager mm;
    auto frame = mm.GetCurrentFrame("", 0, 1.0f);
    EXPECT_EQ(frame.texture_id, 0u);
    EXPECT_EQ(frame.width, 0);
    EXPECT_EQ(frame.height, 0);

    int w = -1, h = -1;
    EXPECT_FALSE(mm.GetMovieDimensions("nonexistent_video.mp4", w, h));
    EXPECT_EQ(w, -1);
    EXPECT_EQ(h, -1);
}

TEST(MovieManagerTest, SyntheticClipRegistersAndReportsDimensions) {
    MovieManager mm;
    std::vector<int64_t> durations = {100, 200, 300};
    std::vector<std::vector<uint8_t>> frames(
        3, std::vector<uint8_t>(4 * 4 * 4, 255));

    EXPECT_TRUE(
        mm.RegisterSyntheticClip("test_anim", 4, 4, durations, frames));

    int w = 0, h = 0;
    EXPECT_TRUE(mm.GetMovieDimensions("test_anim", w, h));
    EXPECT_EQ(w, 4);
    EXPECT_EQ(h, 4);
}

TEST(MovieManagerTest, LoopingPlaybackFrameProgression) {
    MovieManager mm;
    // 3 frames: 0..100ms (frame 0), 100..300ms (frame 1), 300..600ms (frame 2)
    std::vector<int64_t> durations = {100, 200, 300};
    std::vector<std::vector<uint8_t>> frames(
        3, std::vector<uint8_t>(4 * 4 * 4, 0));

    ASSERT_TRUE(
        mm.RegisterSyntheticClip("anim_loop", 4, 4, durations, frames));

    // Initial frame at t=0ms
    auto f0 = mm.GetCurrentFrame("anim_loop", 0, 1.0f);
    EXPECT_EQ(f0.frame_index, 0);

    // Advance to t=150ms -> should be frame 1 (100..300ms)
    auto f1 = mm.GetCurrentFrame("anim_loop", 150, 1.0f);
    EXPECT_EQ(f1.frame_index, 1);

    // Advance to t=450ms -> should be frame 2 (300..600ms)
    auto f2 = mm.GetCurrentFrame("anim_loop", 450, 1.0f);
    EXPECT_EQ(f2.frame_index, 2);

    // Advance to t=650ms (delta +200ms -> clock 650 % 600 = 50ms) -> wraps
    auto f_loop = mm.GetCurrentFrame("anim_loop", 650, 1.0f);
    EXPECT_EQ(f_loop.frame_index, 0);
}

TEST(MovieManagerTest, PlaybackSpeedMultiplier) {
    MovieManager mm;
    // 2 frames: 0..100ms (frame 0), 100..200ms (frame 1)
    std::vector<int64_t> durations = {100, 100};
    std::vector<std::vector<uint8_t>> frames(
        2, std::vector<uint8_t>(2 * 2 * 4, 128));

    ASSERT_TRUE(
        mm.RegisterSyntheticClip("speed_test", 2, 2, durations, frames));

    // At t=0
    auto f0 = mm.GetCurrentFrame("speed_test", 0, 2.0f);
    EXPECT_EQ(f0.frame_index, 0);

    // At t=60ms with 2.0x speed -> effective delta 120ms -> in frame 1!
    auto f1 = mm.GetCurrentFrame("speed_test", 60, 2.0f);
    EXPECT_EQ(f1.frame_index, 1);
}

TEST(MovieManagerTest, RenderMovieQuadHandlesFallbackSafely) {
    MovieManager mm;
    RenderCommand cmd;
    cmd.type = RenderCommand::Type::TexturedQuad;
    cmd.pixel_rect = {10.0f, 10.0f, 100.0f, 80.0f};
    cmd.texture_asset = "missing_movie.gif";
    cmd.opacity = 0.5f;
    cmd.fit = "scale";
    cmd.tilt_deg = 3.0f;
    cmd.is_movie = true;

    EXPECT_NO_THROW(mm.RenderMovieQuad(cmd, 100));
}

TEST(MovieManagerTest, LoadsRealMp4VideoWhenPresent) {
    const std::string video_path = "C:\\Users\\ebomi\\Videos\\Sequence 05.mp4";
    if (!std::filesystem::exists(video_path)) {
        GTEST_SKIP() << "Test video file not found, skipping real decode test.";
    }

    MovieManager mm;
    int w = 0, h = 0;
    EXPECT_TRUE(mm.GetMovieDimensions(video_path, w, h));
    EXPECT_GT(w, 0);
    EXPECT_GT(h, 0);

    auto frame = mm.GetCurrentFrame(video_path, 0, 1.0f);
    EXPECT_EQ(frame.width, w);
    EXPECT_EQ(frame.height, h);

    // Advance playback time
    auto frame_later = mm.GetCurrentFrame(video_path, 500, 1.0f);
    EXPECT_EQ(frame_later.width, w);
    EXPECT_EQ(frame_later.height, h);
}

TEST(MovieManagerTest, UnloadAllClearsClips) {
    MovieManager mm;
    std::vector<int64_t> durations = {100};
    std::vector<std::vector<uint8_t>> frames(1, std::vector<uint8_t>(4, 0));
    mm.RegisterSyntheticClip("clip", 1, 1, durations, frames);

    int w = 0, h = 0;
    EXPECT_TRUE(mm.GetMovieDimensions("clip", w, h));

    mm.UnloadAll();
    EXPECT_FALSE(mm.GetMovieDimensions("clip", w, h));
}

}  // namespace live_renderer

