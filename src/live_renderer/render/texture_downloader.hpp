/**
 * @file texture_downloader.hpp
 * @brief Header for TextureDownloader handling HTTP/HTTPS image downloads.
 *
 * Provides thread-safe HTTP/HTTPS image downloading with local disk caching
 * and asynchronous background download support.
 *
 * Usage:
 *   live_renderer::TextureDownloader downloader;
 *   std::string path = downloader.DownloadSync(url);
 */

#ifndef LIVE_RENDERER_RENDER_TEXTURE_DOWNLOADER_HPP_
#define LIVE_RENDERER_RENDER_TEXTURE_DOWNLOADER_HPP_

#include <functional>
#include <mutex>
#include <string>
#include <unordered_set>
#include <vector>

namespace live_renderer {

using HttpImageFetchFn =
    std::function<std::vector<uint8_t>(const std::string& url)>;

/**
 * @brief Downloads image files from HTTP/HTTPS URLs and caches them locally.
 *
 * Single responsibility: Handles network transfer of image assets and disk
 * caching, keeping OpenGL and rendering code completely decoupled from HTTP.
 */
class TextureDownloader {
 public:
    explicit TextureDownloader(
        std::string cache_dir = ".cache/textures",
        HttpImageFetchFn custom_fetcher = nullptr);
    ~TextureDownloader();

    TextureDownloader(const TextureDownloader&) = delete;
    TextureDownloader& operator=(const TextureDownloader&) = delete;

    /**
     * @brief Checks if a given asset path is an HTTP or HTTPS URL.
     *
     * @param path Asset path or URL.
     * @return bool True if path begins with http:// or https://.
     */
    static bool IsHttpUrl(const std::string& path);

    /**
     * @brief Checks if a URL is already downloaded and present on disk.
     *
     * @param url Remote image URL.
     * @return std::string Path to cached file on disk, or empty if not cached.
     */
    std::string GetCachedFilePath(const std::string& url) const;

    /**
     * @brief Synchronously downloads a URL and saves it to the disk cache.
     *
     * @param url Remote image URL.
     * @return std::string Path to cached file, or empty string on failure.
     */
    std::string DownloadSync(const std::string& url);

    /**
     * @brief Requests an asynchronous background download of a URL.
     *
     * Does nothing if already cached, downloading, or previously failed.
     *
     * @param url Remote image URL.
     */
    void RequestDownloadAsync(const std::string& url);

    /**
     * @brief Checks whether a URL has previously failed downloading.
     *
     * @param url Remote image URL.
     * @return bool True if download previously failed.
     */
    bool HasFailed(const std::string& url) const;

    /**
     * @brief Polls completed background downloads and invokes callback.
     *
     * Must be called on the main/render thread so textures can be loaded.
     *
     * @param on_complete Callback invoked with (url, cached_file_path).
     */
    void PollCompletedDownloads(
        const std::function<void(
            const std::string& url,
            const std::string& cached_path)>& on_complete);

    /**
     * @brief Sets a custom HTTP fetcher function (primarily for unit testing).
     *
     * @param fetcher Injected function that takes a URL and returns raw bytes.
     */
    void SetCustomFetcher(HttpImageFetchFn fetcher);

 private:
    std::string cache_dir_;
    HttpImageFetchFn custom_fetcher_;

    mutable std::mutex mutex_;
    std::unordered_set<std::string> pending_urls_;
    std::unordered_set<std::string> failed_urls_;
    std::vector<std::pair<std::string, std::string>> completed_downloads_;

    std::string GetCacheFilename(const std::string& url) const;
    static std::vector<uint8_t> DefaultWinHttpDownload(const std::string& url);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_TEXTURE_DOWNLOADER_HPP_

