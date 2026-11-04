/**
 * @file movie_manager.hpp
 * @brief Header for MovieManager managing looped playback and video textures.
 *
 * Provides loading, caching, frame decoding, looping playback timing, and
 * OpenGL rendering for movie clip components.
 *
 * Usage:
 *   live_renderer::MovieManager movies;
 *   movies.RenderMovieQuad(cmd, current_time_ms);
 */

#ifndef LIVE_RENDERER_RENDER_MOVIE_MANAGER_HPP_
#define LIVE_RENDERER_RENDER_MOVIE_MANAGER_HPP_

#include <SDL_opengl.h>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "live_renderer/render/mf_video_reader.hpp"
#include "live_renderer/render/render_batch.hpp"

namespace live_renderer {

/**
 * @brief Current frame texture metadata for a movie clip.
 */
struct MovieFrameInfo {
    GLuint texture_id = 0;
    int width = 0;
    int height = 0;
    int frame_index = 0;
    int64_t timestamp_ms = 0;
};

/**
 * @brief Represents a single decoded video/animation frame.
 */
struct MovieFrame {
    int64_t start_ms = 0;
    int64_t duration_ms = 100;
    std::vector<uint8_t> rgba_bytes;
};

/**
 * @brief Internal representation of a cached movie clip.
 */
struct MovieClip {
    std::string path;
    int width = 0;
    int height = 0;
    int64_t total_duration_ms = 0;
    std::vector<MovieFrame> frames;

    GLuint texture_id = 0;
    int active_frame_index = -1;
    int64_t last_time_ms = -1;
    double playback_clock_ms = 0.0;
    std::unique_ptr<MfVideoReader> video_reader;
};

/**
 * @brief Manages loading, caching, timing, and rendering of movie clips.
 *
 * Single responsibility: Handles lifetime and drawing of looped movie clips
 * with playback speed multiplier, opacity, and fit modes.
 */
class MovieManager {
 public:
    MovieManager() = default;
    ~MovieManager();

    MovieManager(const MovieManager&) = delete;
    MovieManager& operator=(const MovieManager&) = delete;

    /**
     * @brief Retrieves the current frame texture and dimensions for a clip.
     *
     * @param asset_path Path to movie file.
     * @param current_time_ms Current presentation time in milliseconds.
     * @param playback_speed Multiplier for playback speed (default 1.0).
     * @return MovieFrameInfo OpenGL texture ID and frame dimensions.
     */
    MovieFrameInfo GetCurrentFrame(
        const std::string& asset_path,
        int64_t current_time_ms,
        float playback_speed = 1.0f);

    /**
     * @brief Retrieves movie dimensions.
     *
     * @param asset_path Path to movie file.
     * @param out_width Receives pixel width.
     * @param out_height Receives pixel height.
     * @return bool True if movie was found and dimensions retrieved.
     */
    bool GetMovieDimensions(
        const std::string& asset_path, int& out_width, int& out_height);

    /**
     * @brief Renders a movie quad with fit mode, opacity, and tilt.
     *
     * @param cmd Render command specifying pixel_rect, texture_asset, opacity.
     * @param current_time_ms Current presentation time in milliseconds.
     */
    void RenderMovieQuad(
        const RenderCommand& cmd,
        int64_t current_time_ms);

    /**
     * @brief Registers synthetic/mock movie frames for testing.
     *
     * @param clip_id Identifier path to associate with this clip.
     * @param width Frame pixel width.
     * @param height Frame pixel height.
     * @param frame_durations_ms Duration in milliseconds for each frame.
     * @param frames_rgba List of raw RGBA pixel byte buffers.
     * @return bool True if registered successfully.
     */
    bool RegisterSyntheticClip(
        const std::string& clip_id,
        int width,
        int height,
        const std::vector<int64_t>& frame_durations_ms,
        const std::vector<std::vector<uint8_t>>& frames_rgba);

    /**
     * @brief Unloads and deletes all cached OpenGL textures and clips.
     */
    void UnloadAll();

 private:
    std::unordered_map<std::string, std::unique_ptr<MovieClip>> cache_;

    std::string ResolveAssetPath(const std::string& asset_path) const;
    bool LoadClip(const std::string& resolved_path, MovieClip& out_clip);
    bool LoadGifClip(const std::string& resolved_path, MovieClip& out_clip);
    void UpdateClipPlayback(
        MovieClip& clip,
        int64_t current_time_ms,
        float playback_speed);
    void UpdateVideoPlayback(
        MovieClip& clip,
        int64_t current_time_ms,
        float playback_speed);
    void UploadActiveFrame(MovieClip& clip, int frame_index);
    void UploadVideoFrame(MovieClip& clip);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_MOVIE_MANAGER_HPP_

