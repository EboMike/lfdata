/**
 * @file shake_tracker.hpp
 * @brief State tracking and random translation calculation for shake effects.
 *
 * Tracks the active duration and progress of shake effects for UI elements
 * and templates when triggered (such as when a player goes down).
 * Manages decay so that translation strength diminishes linearly from
 * initial strength to 0 over the configured duration.
 *
 * Usage example:
 *   live_renderer::ShakeTracker tracker;
 *   auto [dx, dy] = tracker.GetShakeOffset(
 *       "player_10", is_down, current_time_ms, 0.5f, 10.0f);
 */

#ifndef LIVE_RENDERER_COMPONENTS_SHAKE_TRACKER_HPP_
#define LIVE_RENDERER_COMPONENTS_SHAKE_TRACKER_HPP_

#include <cstdint>
#include <string>
#include <unordered_map>
#include <utility>
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Tracks time-dependent shake animations for visual elements.
 *
 * Stores the starting time when an entity becomes active and produces
 * decaying pseudo-random translations in X and Y.
 */
class ShakeTracker {
 public:
    ShakeTracker() = default;
    ~ShakeTracker() = default;

    /**
     * @brief Evaluates the current shake offset for a named tracking key.
     *
     * @param key Unique identifier for the element or template instance.
     * @param is_active True if the triggering condition (e.g. down) holds.
     * @param current_time_ms Current monotonic or simulation time in ms.
     * @param duration_sec Total duration of the shake in seconds.
     * @param strength Maximum translation magnitude in pixels.
     * @param seed Optional seed for reproducible testing (0 uses time hash).
     * @return std::pair<float, float> of (delta_x, delta_y) in pixels.
     *
     * Usage example:
     *   auto [dx, dy] = tracker.GetShakeOffset("k", true, 1000, 0.5f, 8.0f);
     */
    std::pair<float, float> GetShakeOffset(
        const std::string& key,
        bool is_active,
        int64_t current_time_ms,
        float duration_sec,
        float strength,
        uint32_t seed = 0);

    /**
     * @brief Computes a single decayed shake offset given elapsed time.
     *
     * Pure function used for direct deterministic evaluation and testing.
     *
     * @param elapsed_sec Elapsed seconds since shake started.
     * @param duration_sec Total duration in seconds.
     * @param strength Maximum initial translation in pixels.
     * @param seed Random generator seed.
     * @return std::pair<float, float> of (delta_x, delta_y).
     *
     * Usage example:
     *   auto [dx, dy] =
     *       ShakeTracker::ComputeShakeOffset(0.1f, 0.5f, 10.0f, 42);
     */
    static std::pair<float, float> ComputeShakeOffset(
        float elapsed_sec,
        float duration_sec,
        float strength,
        uint32_t seed = 0);

    /**
     * @brief Resets all tracked shake states.
     *
     * Usage example:
     *   tracker.Reset();
     */
    void Reset();

    /**
     * @brief Removes a single tracked key from state.
     *
     * @param key Key to remove.
     *
     * Usage example:
     *   tracker.ClearKey("player_10");
     */
    void ClearKey(const std::string& key);

 private:
    struct State {
        int64_t start_time_ms = -1;
        bool was_active = false;
    };

    std::unordered_map<std::string, State> states_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_SHAKE_TRACKER_HPP_
