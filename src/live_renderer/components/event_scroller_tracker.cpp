/**
 * @file event_scroller_tracker.cpp
 * @brief Implementation of EventScrollerTracker for smooth scroll animations.
 */

#include "live_renderer/components/event_scroller_tracker.hpp"
#include <algorithm>

namespace live_renderer {

namespace {

constexpr float kPi = 3.14159265358979323846f;

float ComputeProgress(float raw_t, const std::string& anim_type) {
    float clamped_t = std::clamp(raw_t, 0.0f, 1.0f);
    if (anim_type == "linear") {
        return clamped_t;
    }
    if (anim_type == "none") {
        return 1.0f;
    }
    // Default to ease-in-and-ease-out cosine curve
    return 0.5f * (1.0f - std::cos(clamped_t * kPi));
}

}  // namespace

void EventScrollerTracker::Reset() {
    tracks_.clear();
}

float EventScrollerTracker::GetScrollOffset(
    const std::string& scroller_key,
    size_t num_events,
    float step_y,
    int64_t current_time_ms,
    const std::string& anim_type,
    float duration_seconds) {
    if (num_events == 0) {
        tracks_.erase(scroller_key);
        return 0.0f;
    }

    const int idx = static_cast<int>(num_events) - 1;
    const float target_offset = static_cast<float>(idx) * step_y;

    auto it = tracks_.find(scroller_key);
    if (it == tracks_.end() || !it->second.initialized) {
        ScrollerTrack tr;
        tr.current_scroll = target_offset;
        tr.start_scroll = target_offset;
        tr.target_scroll = target_offset;
        tr.start_time_ms = current_time_ms;
        tr.duration_ms = duration_seconds > 0.0f
            ? static_cast<int64_t>(duration_seconds * 1000.0f)
            : 500;
        tr.last_event_count = num_events;
        tr.anim_type = anim_type;
        tr.initialized = true;
        tracks_[scroller_key] = tr;
        return target_offset;
    }

    ScrollerTrack& tr = it->second;

    if (anim_type == "none" || duration_seconds <= 0.0f ||
        current_time_ms <= 0) {
        tr.current_scroll = target_offset;
        tr.start_scroll = target_offset;
        tr.target_scroll = target_offset;
        tr.duration_ms = 0;
        tr.last_event_count = num_events;
        return target_offset;
    }

    // Handle buffer pruning (e.g. older items dropped in live_state_store)
    if (num_events < tr.last_event_count) {
        size_t dropped = tr.last_event_count - num_events;
        if (dropped <= 100) {
            float shift = static_cast<float>(dropped) * step_y;
            tr.start_scroll = std::max(0.0f, tr.start_scroll - shift);
            tr.current_scroll = std::max(0.0f, tr.current_scroll - shift);
            tr.target_scroll = target_offset;
            tr.last_event_count = num_events;
        } else {
            // Full session reset
            tr.current_scroll = target_offset;
            tr.start_scroll = target_offset;
            tr.target_scroll = target_offset;
            tr.duration_ms = 0;
            tr.last_event_count = num_events;
            tr.start_time_ms = current_time_ms;
            return target_offset;
        }
    }

    // If target position changed (new event arrived), initiate transition
    if (std::abs(target_offset - tr.target_scroll) > 0.01f) {
        float visual_now = tr.current_scroll;
        if (tr.duration_ms > 0) {
            int64_t elapsed = current_time_ms - tr.start_time_ms;
            if (elapsed < tr.duration_ms && elapsed >= 0) {
                float raw_p = static_cast<float>(elapsed) /
                              static_cast<float>(tr.duration_ms);
                float eased_p = ComputeProgress(raw_p, tr.anim_type);
                visual_now = tr.start_scroll +
                    (tr.target_scroll - tr.start_scroll) * eased_p;
            } else if (elapsed >= tr.duration_ms) {
                visual_now = tr.target_scroll;
            }
        }
        tr.start_scroll = visual_now;
        tr.target_scroll = target_offset;
        tr.start_time_ms = current_time_ms;
        tr.duration_ms = static_cast<int64_t>(duration_seconds * 1000.0f);
        if (tr.duration_ms <= 0) tr.duration_ms = 500;
        tr.anim_type = anim_type;
        tr.last_event_count = num_events;
    }

    // Evaluate active animation progress
    if (tr.duration_ms <= 0) {
        tr.current_scroll = tr.target_scroll;
        return tr.target_scroll;
    }

    int64_t elapsed = current_time_ms - tr.start_time_ms;
    if (elapsed >= tr.duration_ms) {
        tr.current_scroll = tr.target_scroll;
        return tr.target_scroll;
    }
    if (elapsed < 0) {
        // Clock jitter guard
        tr.current_scroll = tr.start_scroll;
        return tr.start_scroll;
    }

    float raw_p = static_cast<float>(elapsed) /
                  static_cast<float>(tr.duration_ms);
    float eased_p = ComputeProgress(raw_p, tr.anim_type);
    tr.current_scroll =
        tr.start_scroll + (tr.target_scroll - tr.start_scroll) * eased_p;
    return tr.current_scroll;
}

}  // namespace live_renderer

