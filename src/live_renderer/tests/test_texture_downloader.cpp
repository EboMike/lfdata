/**
 * @file test_texture_downloader.cpp
 * @brief Unit tests for TextureDownloader HTTP downloading and disk caching.
 */

#include <gtest/gtest.h>
#include <chrono>
#include <filesystem>
#include <thread>
#include "live_renderer/render/texture_downloader.hpp"

namespace live_renderer {

TEST(TextureDownloaderTest, DetectsHttpAndHttpsUrls) {
    EXPECT_TRUE(TextureDownloader::IsHttpUrl("http://example.com/pic.png"));
    EXPECT_TRUE(TextureDownloader::IsHttpUrl("https://example.com/avatar.jpg"));
    EXPECT_FALSE(TextureDownloader::IsHttpUrl("assets/sm5/commander.png"));
    EXPECT_FALSE(TextureDownloader::IsHttpUrl("C:\\images\\pic.png"));
    EXPECT_FALSE(TextureDownloader::IsHttpUrl(""));
}

TEST(TextureDownloaderTest, DownloadSyncWithCustomFetcherCachesFile) {
    namespace fs = std::filesystem;
    std::string test_cache = ".cache/test_textures_sync";
    fs::remove_all(test_cache);

    int call_count = 0;
    auto mock_fetcher = [&call_count](const std::string& url)
        -> std::vector<uint8_t> {
        ++call_count;
        return {'P', 'N', 'G', '1', '2', '3'};
    };

    TextureDownloader downloader(test_cache, mock_fetcher);
    std::string url = "https://example.com/test_avatar.png";

    EXPECT_EQ(downloader.GetCachedFilePath(url), "");
    std::string cached_path = downloader.DownloadSync(url);

    EXPECT_FALSE(cached_path.empty());
    EXPECT_TRUE(fs::exists(cached_path));
    EXPECT_EQ(call_count, 1);

    // Second call should hit the disk cache and not invoke fetcher
    std::string cached_again = downloader.DownloadSync(url);
    EXPECT_EQ(cached_again, cached_path);
    EXPECT_EQ(call_count, 1);

    fs::remove_all(test_cache);
}

TEST(TextureDownloaderTest, DownloadSyncFailureMarksAsFailed) {
    namespace fs = std::filesystem;
    std::string test_cache = ".cache/test_textures_fail";
    fs::remove_all(test_cache);

    auto fail_fetcher = [](const std::string& url) -> std::vector<uint8_t> {
        return {};
    };

    TextureDownloader downloader(test_cache, fail_fetcher);
    std::string url = "https://example.com/missing.png";

    EXPECT_FALSE(downloader.HasFailed(url));
    std::string res = downloader.DownloadSync(url);
    EXPECT_EQ(res, "");
    EXPECT_TRUE(downloader.HasFailed(url));

    fs::remove_all(test_cache);
}

TEST(TextureDownloaderTest, RequestDownloadAsyncCompletesAndPolls) {
    namespace fs = std::filesystem;
    std::string test_cache = ".cache/test_textures_async";
    fs::remove_all(test_cache);

    auto mock_fetcher = [](const std::string& url) -> std::vector<uint8_t> {
        return {'T', 'E', 'S', 'T', 'D', 'A', 'T', 'A'};
    };

    TextureDownloader downloader(test_cache, mock_fetcher);
    std::string url = "https://example.com/async_avatar.png";

    downloader.RequestDownloadAsync(url);

    // Wait briefly for the worker thread to finish
    std::string completed_url;
    std::string completed_path;
    for (int i = 0; i < 20; ++i) {
        downloader.PollCompletedDownloads(
            [&](const std::string& u, const std::string& p) {
                completed_url = u;
                completed_path = p;
            });
        if (!completed_url.empty()) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    EXPECT_EQ(completed_url, url);
    EXPECT_FALSE(completed_path.empty());
    EXPECT_TRUE(fs::exists(completed_path));

    fs::remove_all(test_cache);
}

}  // namespace live_renderer

