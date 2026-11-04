/**
 * @file list_animation_tracker.cpp
 * @brief Implementation of ListAnimationTracker for list reordering animations.
 */

#include "live_renderer/components/list_animation_tracker.hpp"

#include <algorithm>
#include <cmath>

namespace live_renderer {

ListAnimationType ListAnimationTracker::ParseAnimationType(
    std::string_view type_name) {
    if (type_name.empty()) return ListAnimationType::None;

    std::string lower;
    lower.reserve(type_name.size());
    for (char c : type_name) {
        lower.push_back(
            static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }

    if (lower == "linear") {
        return ListAnimationType::Linear;
    }
    if (lower == "ease-in-and-ease-out" || lower == "ease_in_out" ||
        lower == "easeinout") {
        return ListAnimationType::EaseInOut;
    }
    return ListAnimationType::None;
}

std::string ListAnimationTracker::FormatAnimationType(
    ListAnimationType type) {
    switch (type) {
        case ListAnimationType::Linear:
            return "linear";
        case ListAnimationType::EaseInOut:
            return "ease-in-and-ease-out";
        case ListAnimationType::None:
        default:
            return "none";
    }
}

std::string ListAnimationTracker::MakeKey(
    const std::string& list_id, int item_id) {
    return list_id + ":" + std::to_string(item_id);
}

float ListAnimationTracker::ComputeProgress(
    float t, ListAnimationType anim_type) {
    const float clamped_t = std::clamp(t, 0.0f, 1.0f);
    switch (anim_type) {
        case ListAnimationType::Linear:
            return clamped_t;
        case ListAnimationType::EaseInOut: {
            constexpr float kPi = 3.14159265358979323846f;
            return 0.5f * (1.0f - std::cos(clamped_t * kPi));
        }
        case ListAnimationType::None:
        default:
            return 1.0f;
    }
}

void ListAnimationTracker::Reset() {
    tracks_.clear();
}

float ListAnimationTracker::GetAnimatedPosition(
    const std::string& list_id,
    int item_id,
    float target_pos,
    int64_t current_time_ms,
    ListAnimationType anim_type,
    float duration_seconds) {
    std::string key = MakeKey(list_id, item_id);
    auto it = tracks_.find(key);

    if (it == tracks_.end() || !it->second.initialized) {
        ItemTrack tr;
        tr.current_pos = target_pos;
        tr.start_pos = target_pos;
        tr.target_pos = target_pos;
        tr.start_time_ms = current_time_ms;
        tr.duration_ms = 0;
        tr.anim_type = anim_type;
        tr.initialized = true;
        tracks_[key] = tr;
        return target_pos;
    }

    ItemTrack& tr = it->second;

    if (anim_type == ListAnimationType::None || duration_seconds <= 0.0f) {
        tr.current_pos = target_pos;
        tr.start_pos = target_pos;
        tr.target_pos = target_pos;
        tr.duration_ms = 0;
        return target_pos;
    }

    // If target position changed, start transitioning from current position
    if (std::abs(target_pos - tr.target_pos) > 0.01f) {
        float start_from = tr.current_pos;
        if (tr.duration_ms > 0) {
            int64_t elapsed = current_time_ms - tr.start_time_ms;
            if (elapsed < tr.duration_ms && elapsed >= 0) {
                float raw_p = static_cast<float>(elapsed) /
                              static_cast<float>(tr.duration_ms);
                float eased_p = ComputeProgress(raw_p, tr.anim_type);
                start_from =
                    tr.start_pos + (tr.target_pos - tr.start_pos) * eased_p;
            } else {
                start_from = tr.target_pos;
            }
        }
        tr.start_pos = start_from;
        tr.current_pos = start_from;
        tr.target_pos = target_pos;
        tr.start_time_ms = current_time_ms;
        tr.duration_ms = static_cast<int64_t>(duration_seconds * 1000.0f);
        tr.anim_type = anim_type;
    }

    if (tr.duration_ms <= 0) {
        tr.current_pos = target_pos;
        return target_pos;
    }

    int64_t elapsed = current_time_ms - tr.start_time_ms;
    if (elapsed >= tr.duration_ms) {
        tr.current_pos = tr.target_pos;
        return tr.target_pos;
    }

    float raw_p = std::clamp(
        static_cast<float>(elapsed) / static_cast<float>(tr.duration_ms),
        0.0f,
        1.0f);
    float eased_p = ComputeProgress(raw_p, tr.anim_type);
    tr.current_pos =
        tr.start_pos + (tr.target_pos - tr.start_pos) * eased_p;
    return tr.current_pos;
}

float ListAnimationTracker::GetAnimatedPosition(
    const std::string& list_id,
    int item_id,
    float target_pos,
    int64_t current_time_ms,
    std::string_view anim_type_str,
    float duration_seconds) {
    return GetAnimatedPosition(
        list_id,
        item_id,
        target_pos,
        current_time_ms,
        ParseAnimationType(anim_type_str),
        duration_seconds);
}

}  // namespace live_renderer

