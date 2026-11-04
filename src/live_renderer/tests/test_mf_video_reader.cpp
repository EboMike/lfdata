/**
 * @file test_mf_video_reader.cpp
 * @brief Unit tests for MfVideoReader Windows Media Foundation video playback.
 */

#include <filesystem>
#include <gtest/gtest.h>
#include "live_renderer/render/mf_video_reader.hpp"

namespace live_renderer {

TEST(MfVideoReaderTest, EmptyPathReturnsFalse) {
    MfVideoReader reader;
    EXPECT_FALSE(reader.Open(""));
    EXPECT_FALSE(reader.IsOpen());
    EXPECT_EQ(reader.GetWidth(), 0);
    EXPECT_EQ(reader.GetHeight(), 0);
    EXPECT_EQ(reader.GetDurationMs(), 0);
    EXPECT_TRUE(reader.GetCurrentFrameRgba().empty());
}

TEST(MfVideoReaderTest, NonExistentFileReturnsFalse) {
    MfVideoReader reader;
    EXPECT_FALSE(reader.Open("nonexistent_video_file_12345.mp4"));
    EXPECT_FALSE(reader.IsOpen());
}

TEST(MfVideoReaderTest, ClosedReaderOperationsFailGracefully) {
    MfVideoReader reader;
    EXPECT_FALSE(reader.SeekToMs(500));
    EXPECT_FALSE(reader.UpdateToTimeMs(500));
    EXPECT_EQ(reader.GetCurrentTimestampMs(), -1);
    reader.Close();
    EXPECT_FALSE(reader.IsOpen());
}

TEST(MfVideoReaderTest, MoveConstructionAndAssignment) {
    MfVideoReader r1;
    MfVideoReader r2(std::move(r1));
    EXPECT_FALSE(r2.IsOpen());

    MfVideoReader r3;
    r3 = std::move(r2);
    EXPECT_FALSE(r3.IsOpen());
}

TEST(MfVideoReaderTest, PlaysRealVideoFileWhenPresent) {
    const std::string video_path = "C:\\Users\\ebomi\\Videos\\Sequence 05.mp4";
    if (!std::filesystem::exists(video_path)) {
        GTEST_SKIP() << "Test video file not found, skipping real decode test.";
    }

    MfVideoReader reader;
    ASSERT_TRUE(reader.Open(video_path));
    EXPECT_TRUE(reader.IsOpen());

    const int width = reader.GetWidth();
    const int height = reader.GetHeight();
    const int64_t duration_ms = reader.GetDurationMs();

    EXPECT_GT(width, 0);
    EXPECT_GT(height, 0);
    EXPECT_GT(duration_ms, 0);

    const auto& frame_rgba = reader.GetCurrentFrameRgba();
    EXPECT_EQ(
        frame_rgba.size(),
        static_cast<size_t>(width) * height * 4);

    // Update time forward within video duration
    const int64_t test_time_ms = std::min<int64_t>(duration_ms / 2, 1000);
    reader.UpdateToTimeMs(test_time_ms);
    EXPECT_GE(reader.GetCurrentTimestampMs(), 0);

    // Seek back to start
    EXPECT_TRUE(reader.SeekToMs(0));
    EXPECT_GE(reader.GetCurrentTimestampMs(), 0);

    reader.Close();
    EXPECT_FALSE(reader.IsOpen());
}

}  // namespace live_renderer

