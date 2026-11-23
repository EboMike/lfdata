/**
 * @file rtsp_feed_reader.hpp
 * @brief Interface and implementation for live RTSP video feed decoding.
 *
 * Provides URL validation and non-blocking background decoding of RTSP streams
 * into 32-bit RGBA pixel buffers so render threads never block on network I/O.
 *
 * Usage example:
 * @code
 * live_renderer::RtspFeedReader reader;
 * reader.Open("rtsp://192.168.1.100:554/stream1");
 * std::vector<uint8_t> rgba;
 * int w = 0, h = 0;
 * uint64_t seq = 0;
 * if (reader.CopyLatestFrameRgba(rgba, w, h, seq)) {
 *     // Upload rgba to GPU texture
 * }
 * @endcode
 */

#ifndef LIVE_RENDERER_FEEDS_RTSP_FEED_READER_HPP_
#define LIVE_RENDERER_FEEDS_RTSP_FEED_READER_HPP_

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace live_renderer {

/**
 * @brief Connection lifecycle states for a live feed stream.
 */
enum class FeedConnectionState {
    kDisconnected,
    kConnecting,
    kConnected,
    kError
};

/**
 * @brief Abstract interface for a live video feed reader.
 */
class IFeedReader {
public:
    virtual ~IFeedReader() = default;

    /**
     * @brief Validates the URL and begins connecting asynchronously.
     *
     * @param url Stream URL (e.g. rtsp://...).
     * @return True if the URL is syntactically valid and connection started,
     *         false if the URL is invalid (sets error message).
     */
    virtual bool Open(const std::string& url) = 0;

    /**
     * @brief Closes the stream and stops any background decoding thread.
     */
    virtual void Close() = 0;

    /**
     * @brief Returns true if a stream is currently connecting or connected.
     */
    virtual bool IsOpen() const = 0;

    /**
     * @brief Returns the current connection state.
     */
    virtual FeedConnectionState GetState() const = 0;

    /**
     * @brief Returns the last error message if state is kError, or empty.
     */
    virtual std::string GetErrorMessage() const = 0;

    /**
     * @brief Returns the URL passed to Open().
     */
    virtual std::string GetUrl() const = 0;

    /**
     * @brief Returns the decoded frame width in pixels, or 0 if unknown.
     */
    virtual int GetWidth() const = 0;

    /**
     * @brief Returns the decoded frame height in pixels, or 0 if unknown.
     */
    virtual int GetHeight() const = 0;

    /**
     * @brief Returns the monotonic frame sequence number (0 if no frame yet).
     */
    virtual uint64_t GetFrameSequence() const = 0;

    /**
     * @brief Copies the latest decoded RGBA frame if newer than out_seq.
     *
     * @param out_rgba Destination buffer for RGBA bytes (w * h * 4).
     * @param out_width Receives frame width in pixels.
     * @param out_height Receives frame height in pixels.
     * @param in_out_seq In: last seen sequence; Out: new sequence if copied.
     * @return True if a new frame was copied, false otherwise.
     */
    virtual bool CopyLatestFrameRgba(
        std::vector<uint8_t>& out_rgba,
        int& out_width,
        int& out_height,
        uint64_t& in_out_seq) const = 0;
};

using FeedReaderFactory = std::function<std::unique_ptr<IFeedReader>()>;

/**
 * @brief Live RTSP stream reader backed by ffprobe/ffmpeg on a worker thread.
 *
 * Probes stream dimensions, launches an ffmpeg subprocess outputting raw RGBA
 * frames over stdout, and buffers the latest frame for non-blocking render
 * thread consumption.
 */
class RtspFeedReader : public IFeedReader {
public:
    explicit RtspFeedReader(bool allow_rtmp = false);
    ~RtspFeedReader() override;

    RtspFeedReader(const RtspFeedReader&) = delete;
    RtspFeedReader& operator=(const RtspFeedReader&) = delete;

    /**
     * @brief Validates whether a string is a syntactically valid RTSP URL.
     *
     * Requires rtsp:// or rtsps:// scheme, a non-empty host, and if a port
     * is specified, a valid integer in [1, 65535].
     *
     * @param url URL string to validate.
     * @param out_error Receives a human-readable error message on failure.
     * @return True if valid, false otherwise.
     */
    static bool ValidateRtspUrl(const std::string& url, std::string& out_error);

    /**
     * @brief Validates whether a string is a syntactically valid stream URL.
     *
     * Accepts rtsp:// and rtsps://, and optionally rtmp:// and rtmps:// when
     * allow_rtmp is true.
     *
     * @param url URL string to validate.
     * @param allow_rtmp Whether rtmp:// and rtmps:// schemes are permitted.
     * @param out_error Receives a human-readable error message on failure.
     * @return True if valid, false otherwise.
     */
    static bool ValidateStreamUrl(
        const std::string& url,
        bool allow_rtmp,
        std::string& out_error);

    bool Open(const std::string& url) override;
    void Close() override;
    bool IsOpen() const override;
    FeedConnectionState GetState() const override;
    std::string GetErrorMessage() const override;
    std::string GetUrl() const override;
    int GetWidth() const override;
    int GetHeight() const override;
    uint64_t GetFrameSequence() const override;
    bool CopyLatestFrameRgba(
        std::vector<uint8_t>& out_rgba,
        int& out_width,
        int& out_height,
        uint64_t& in_out_seq) const override;

private:
    void WorkerLoop(std::string url);

    bool allow_rtmp_ = false;
    mutable std::mutex mutex_;
    std::string url_;
    FeedConnectionState state_ = FeedConnectionState::kDisconnected;
    std::string error_message_;
    int width_ = 0;
    int height_ = 0;
    uint64_t frame_seq_ = 0;
    std::vector<uint8_t> latest_frame_rgba_;

    std::atomic<bool> stop_requested_{false};
    std::thread worker_thread_;

#if defined(_WIN32)
    std::mutex process_mutex_;
    void* active_process_handle_ = nullptr;
#endif
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_FEEDS_RTSP_FEED_READER_HPP_
