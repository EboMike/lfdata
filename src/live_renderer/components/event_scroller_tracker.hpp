/**
 * @file event_scroller_tracker.hpp
 * @brief Header for EventScrollerTracker for smooth event scroller animations.
 *
 * Tracks the visual scroll offset of event scrollers over time, ensuring
 * transitions remain continuous and glitch-free when new events arrive
 * or when events arrive mid-animation.
 *
 * Usage:
 *   live_renderer::EventScrollerTracker tracker;
 *   float y_scroll = tracker.GetScrollOffset(
 *       "main_scroller", num_events, step_y, now_ms,
 *       "ease-in-and-ease-out", 0.5f);
 */

#ifndef LIVE_RENDERER_COMPONENTS_EVENT_SCROLLER_TRACKER_HPP_
#define LIVE_RENDERER_COMPONENTS_EVENT_SCROLLER_TRACKER_HPP_

#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>

namespace live_renderer {

/**
 * @brief Manages smooth vertical scrolling for event scrollers.
 *
 * Single responsibility: Computes animated vertical scroll offsets for
 * scrollers, eliminating jerks and jump discontinuities when events arrive.
 */
class EventScrollerTracker {
 public:
    EventScrollerTracker() = default;
    ~EventScrollerTracker() = default;

    /**
     * @brief Computes animated vertical scroll offset in pixels.
     *
     * @param scroller_key Unique identifier for the scroller element.
     * @param num_events Total count of events currently in the scroller.
     * @param step_y Height in pixels between consecutive event lines.
     * @param current_time_ms Wall clock milliseconds from steady clock.
     * @param anim_type Animation style ("linear", "ease-in-and-ease-out").
     * @param duration_seconds Duration of scroll animation in seconds.
     * @return Current animated scroll offset in pixels.
     */
    float GetScrollOffset(
        const std::string& scroller_key,
        size_t num_events,
        float step_y,
        int64_t current_time_ms,
        const std::string& anim_type = "ease-in-and-ease-out",
        float duration_seconds = 0.5f);

    /**
     * @brief Resets all tracked scrollers.
     */
    void Reset();

 private:
    struct ScrollerTrack {
        float current_scroll = 0.0f;
        float start_scroll = 0.0f;
        float target_scroll = 0.0f;
        int64_t start_time_ms = 0;
        int64_t duration_ms = 500;
        size_t last_event_count = 0;
        std::string anim_type = "ease-in-and-ease-out";
        bool initialized = false;
    };

    std::unordered_map<std::string, ScrollerTrack> tracks_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_EVENT_SCROLLER_TRACKER_HPP_

