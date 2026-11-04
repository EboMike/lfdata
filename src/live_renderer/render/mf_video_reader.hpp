/**
 * @file mf_video_reader.hpp
 * @brief Header for Windows Media Foundation video stream reader.
 *
 * Provides demuxing, decoding, and streaming of video files (e.g., MP4, MOV)
 * using native Windows Media Foundation without requiring external libraries.
 *
 * Usage:
 *   live_renderer::MfVideoReader reader;
 *   if (reader.Open("video.mp4")) {
 *       reader.UpdateToTimeMs(1500);
 *       const auto& rgba = reader.GetCurrentFrameRgba();
 *   }
 */

#ifndef LIVE_RENDERER_RENDER_MF_VIDEO_READER_HPP_
#define LIVE_RENDERER_RENDER_MF_VIDEO_READER_HPP_

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace live_renderer {

/**
 * @brief Streams and decodes video frames via Windows Media Foundation.
 *
 * Single responsibility: Manages an IMFSourceReader session to decode
 * sequential or scrubbed video frames to 32-bit RGBA pixel buffers.
 */
class MfVideoReader {
 public:
    MfVideoReader();
    ~MfVideoReader();

    MfVideoReader(const MfVideoReader&) = delete;
    MfVideoReader& operator=(const MfVideoReader&) = delete;
    MfVideoReader(MfVideoReader&& other) noexcept;
    MfVideoReader& operator=(MfVideoReader&& other) noexcept;

    /**
     * @brief Opens a video file and initializes decoding.
     *
     * Prepares the media source, configures RGB32 output, queries video
     * dimensions and duration, and decodes the initial frame.
     *
     * @param filepath Path to the video file to open.
     * @return bool True if opened and initialized successfully.
     */
    bool Open(const std::string& filepath);

    /**
     * @brief Closes the active video reader and frees resources.
     */
    void Close();

    /**
     * @brief Checks if a video is currently open.
     *
     * @return bool True if a valid reader session is open.
     */
    bool IsOpen() const;

    /**
     * @brief Retrieves video pixel width.
     *
     * @return int Width in pixels, or 0 if not open.
     */
    int GetWidth() const;

    /**
     * @brief Retrieves video pixel height.
     *
     * @return int Height in pixels, or 0 if not open.
     */
    int GetHeight() const;

    /**
     * @brief Retrieves total video duration in milliseconds.
     *
     * @return int64_t Duration in milliseconds.
     */
    int64_t GetDurationMs() const;

    /**
     * @brief Retrieves timestamp of the current decoded frame.
     *
     * @return int64_t Frame presentation time in milliseconds.
     */
    int64_t GetCurrentTimestampMs() const;

    /**
     * @brief Retrieves raw RGBA byte buffer of current frame.
     *
     * @return const std::vector<uint8_t>& RGBA pixel data (w * h * 4 bytes).
     */
    const std::vector<uint8_t>& GetCurrentFrameRgba() const;

    /**
     * @brief Seeks playback to a specific timestamp in milliseconds.
     *
     * @param target_ms Target presentation time in milliseconds.
     * @return bool True if seek and sample decode succeeded.
     */
    bool SeekToMs(int64_t target_ms);

    /**
     * @brief Updates stream to presentation time, decoding if necessary.
     *
     * If target_ms matches current frame, no work is performed. If time
     * has progressed, decodes forward or seeks as needed.
     *
     * @param target_ms Target presentation time in milliseconds.
     * @return bool True if a new frame was decoded and buffer updated.
     */
    bool UpdateToTimeMs(int64_t target_ms);

 private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_MF_VIDEO_READER_HPP_

