/**
 * Client interface for fetching LFstats data in LF Live Renderer.
 *
 * This file provides the LFStatsFetcher class to interact with the LFstats API
 * (https://lfstats.com/api), fetching competition lists, schedules, and
 * match fixtures. It supports asynchronous non-blocking calls across worker
 * threads to ensure continuous rendering remains smooth at all times.
 *
 * Usage example:
 *   live_renderer::LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
 *   auto future = fetcher.FetchCompetitionsAsync();
 *   // In UI render loop:
 *   if (future.wait_for(std::chrono::milliseconds(0)) ==
 *       std::future_status::ready) {
 *       auto competitions = future.get();
 *   }
 */

#ifndef LIVE_RENDERER_LFSTATS_LFSTATS_FETCHER_HPP_
#define LIVE_RENDERER_LFSTATS_LFSTATS_FETCHER_HPP_

#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#include "live_renderer/lfstats/competition_info.hpp"
#include "live_renderer/model/scheduled_game.hpp"

namespace live_renderer {

/**
 * Configuration options for LFStatsFetcher.
 *
 * Attributes:
 *   test_mode: Whether to read test fixtures from local storage.
 *   test_data_dir: Directory path for local fixture JSON files.
 *   base_url: Root API endpoint URL for remote HTTP queries.
 *   timeout_ms: Network request timeout duration in milliseconds.
 *   user_agent: HTTP User-Agent header string.
 *   worker_threads: Number of background worker threads in thread pool.
 */
struct LFStatsFetcherOptions {
    bool test_mode = false;
    std::string test_data_dir = "tests/fixtures/lfstats";
    std::string base_url = "https://lfstats.com/api";
    int64_t timeout_ms = 10000;
    std::string user_agent = "lfdata/1.0";
    size_t worker_threads = 4;
};

/**
 * Client class for fetching competition data from LFstats with multithreading.
 *
 * Provides thread-safe synchronous and asynchronous methods to query
 * competitions and schedules without blocking the rendering pipeline.
 */
class LFStatsFetcher {
public:
    using HttpTransport = std::function<std::string(
        const std::string& url,
        const std::string& user_agent,
        int64_t timeout_ms)>;

    using CompetitionsCallback = std::function<void(
        const std::vector<CompetitionInfo>&,
        const std::string& error)>;

    using ScheduleCallback = std::function<void(
        const std::vector<ScheduledGame>&,
        const std::string& error)>;

    /**
     * Constructs an LFStatsFetcher with default options.
     */
    LFStatsFetcher();

    /**
     * Constructs an LFStatsFetcher with specified options.
     * @param options Configuration options.
     */
    explicit LFStatsFetcher(const LFStatsFetcherOptions& options);

    /**
     * Constructs an LFStatsFetcher with test mode and fixture directory.
     * @param test_mode True to load local fixtures, false for network.
     * @param test_data_dir Path to fixture directory.
     */
    explicit LFStatsFetcher(
        bool test_mode,
        const std::string& test_data_dir = "tests/fixtures/lfstats");

    /**
     * Destructor ensuring background worker threads terminate cleanly.
     */
    ~LFStatsFetcher();

    LFStatsFetcher(const LFStatsFetcher&) = delete;
    LFStatsFetcher& operator=(const LFStatsFetcher&) = delete;
    LFStatsFetcher(LFStatsFetcher&&) = delete;
    LFStatsFetcher& operator=(LFStatsFetcher&&) = delete;

    /**
     * Sets a custom HTTP transport function (e.g. for testing or mocking).
     * @param transport Pluggable transport function.
     */
    void SetHttpTransport(HttpTransport transport);

    /**
     * Checks if test mode is enabled.
     * @return True if reading local fixtures, false otherwise.
     */
    bool IsTestMode() const;

    /**
     * Sets test mode flag.
     * @param test_mode True for local fixture mode.
     */
    void SetTestMode(bool test_mode);

    /**
     * Gets the local test fixture directory path.
     * @return Path string.
     */
    const std::string& GetTestDataDir() const;

    /**
     * Sets the local test fixture directory path.
     * @param dir Directory path string.
     */
    void SetTestDataDir(const std::string& dir);

    /**
     * Gets the base URL for the API endpoint.
     * @return Base URL string.
     */
    const std::string& GetBaseUrl() const;

    /**
     * Sets the base URL for the API endpoint.
     * @param url Base URL string.
     */
    void SetBaseUrl(const std::string& url);

    /**
     * Gets the network timeout in milliseconds.
     * @return Timeout in milliseconds.
     */
    int64_t GetTimeoutMs() const;

    /**
     * Sets the network timeout in milliseconds.
     * @param timeout_ms Timeout in milliseconds.
     */
    void SetTimeoutMs(int64_t timeout_ms);

    /**
     * Gets the HTTP User-Agent header string.
     * @return User-Agent header string.
     */
    const std::string& GetUserAgent() const;

    /**
     * Sets the HTTP User-Agent header string.
     * @param user_agent User-Agent header string.
     */
    void SetUserAgent(const std::string& user_agent);

    /**
     * Gets the number of currently active background tasks.
     * @return Active task count.
     */
    size_t GetActiveTaskCount() const;

    // --- Synchronous methods (Thread-safe) ---

    /**
     * Fetches all competitions synchronously.
     * @return Vector of CompetitionInfo instances.
     * @throws std::runtime_error On network failure or missing fixture.
     */
    std::vector<CompetitionInfo> FetchCompetitions();

    /**
     * Convenience alias for FetchCompetitions.
     * @return Vector of CompetitionInfo instances.
     */
    std::vector<CompetitionInfo> FetchAllCompetitions();

    /**
     * Fetches the competition schedule by competition slug synchronously.
     * @param competition_slug Unique slug of the competition.
     * @return Vector of ScheduledGame instances in order.
     * @throws std::invalid_argument If competition_slug is empty.
     * @throws std::runtime_error On network failure or missing fixture.
     */
    std::vector<ScheduledGame> FetchCompetitionSchedule(
        const std::string& competition_slug);

    /**
     * Convenience alias for FetchCompetitionSchedule.
     * @param competition_slug Unique slug of the competition.
     * @return Vector of ScheduledGame instances.
     */
    std::vector<ScheduledGame> FetchSchedule(
        const std::string& competition_slug);

    // --- Asynchronous Future-based methods (Non-blocking) ---

    /**
     * Fetches all competitions asynchronously via background worker thread.
     * @return std::future holding vector of CompetitionInfo.
     */
    std::future<std::vector<CompetitionInfo>> FetchCompetitionsAsync();

    /**
     * Convenience alias for FetchCompetitionsAsync.
     * @return std::future holding vector of CompetitionInfo.
     */
    std::future<std::vector<CompetitionInfo>> FetchAllCompetitionsAsync();

    /**
     * Fetches competition schedule asynchronously via background thread.
     * @param competition_slug Unique slug of the competition.
     * @return std::future holding vector of ScheduledGame.
     */
    std::future<std::vector<ScheduledGame>> FetchCompetitionScheduleAsync(
        const std::string& competition_slug);

    /**
     * Convenience alias for FetchCompetitionScheduleAsync.
     * @param competition_slug Unique slug of the competition.
     * @return std::future holding vector of ScheduledGame.
     */
    std::future<std::vector<ScheduledGame>> FetchScheduleAsync(
        const std::string& competition_slug);

    // --- Asynchronous Callback-based methods (Non-blocking) ---

    /**
     * Fetches all competitions asynchronously and delivers result to callback.
     * @param callback Function receiving vector of CompetitionInfo and error.
     */
    void FetchCompetitionsAsync(CompetitionsCallback callback);

    /**
     * Fetches competition schedule asynchronously and invokes callback.
     * @param competition_slug Unique slug of the competition.
     * @param callback Function receiving vector of ScheduledGame and error.
     */
    void FetchCompetitionScheduleAsync(
        const std::string& competition_slug,
        ScheduleCallback callback);

private:
    std::string FetchRemoteJson(const std::string& endpoint_path);
    std::string LoadLocalFixture(
        const std::vector<std::string>& candidate_paths,
        const std::string& item_description);
    std::string FetchData(
        const std::string& endpoint_path,
        const std::vector<std::string>& candidate_paths,
        const std::string& item_description);

    template <typename F>
    auto EnqueueTask(F&& f) -> std::future<std::invoke_result_t<F>>;

    LFStatsFetcherOptions options_;
    mutable std::mutex options_mutex_;
    HttpTransport http_transport_;

    // Thread pool state
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> task_queue_;
    mutable std::mutex queue_mutex_;
    std::condition_variable cv_;
    std::atomic<bool> stop_workers_{false};
    std::atomic<size_t> active_tasks_{0};
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_LFSTATS_LFSTATS_FETCHER_HPP_

