/**
 * @file shake_tracker.cpp
 * @brief Implementation of ShakeTracker for element shake effects.
 */

#include "live_renderer/components/shake_tracker.hpp"
#include <algorithm>
#include <random>

namespace live_renderer {

std::pair<float, float> ShakeTracker::ComputeShakeOffset(
    float elapsed_sec,
    float duration_sec,
    float strength,
    uint32_t seed) {
    if (duration_sec <= 0.0f || strength <= 0.0f) {
        return {0.0f, 0.0f};
    }
    if (elapsed_sec < 0.0f || elapsed_sec >= duration_sec) {
        return {0.0f, 0.0f};
    }

    const float progress = std::clamp(elapsed_sec / duration_sec, 0.0f, 1.0f);
    const float cur_strength = strength * (1.0f - progress);

    std::mt19937 rng(seed != 0 ? seed : 12345u);
    std::uniform_real_distribution<float> dist(-1.0f, 1.0f);

    const float rx = dist(rng);
    const float ry = dist(rng);

    return {rx * cur_strength, ry * cur_strength};
}

std::pair<float, float> ShakeTracker::GetShakeOffset(
    const std::string& key,
    bool is_active,
    int64_t current_time_ms,
    float duration_sec,
    float strength,
    uint32_t seed) {
    if (!is_active || duration_sec <= 0.0f || strength <= 0.0f) {
        auto it = states_.find(key);
        if (it != states_.end()) {
            it->second.was_active = false;
            it->second.start_time_ms = -1;
        }
        return {0.0f, 0.0f};
    }

    auto& st = states_[key];
    if (!st.was_active || st.start_time_ms < 0) {
        st.start_time_ms = current_time_ms;
        st.was_active = true;
    }

    const float elapsed_sec =
        static_cast<float>(current_time_ms - st.start_time_ms) / 1000.0f;
    if (elapsed_sec < 0.0f || elapsed_sec >= duration_sec) {
        return {0.0f, 0.0f};
    }

    uint32_t eff_seed = seed;
    if (eff_seed == 0) {
        const uint64_t hash_val = std::hash<std::string>{}(key);
        eff_seed = static_cast<uint32_t>(
            (static_cast<uint64_t>(current_time_ms) * 2654435761u) ^ hash_val);
        if (eff_seed == 0) eff_seed = 1u;
    }

    return ComputeShakeOffset(elapsed_sec, duration_sec, strength, eff_seed);
}

void ShakeTracker::Reset() {
    states_.clear();
}

void ShakeTracker::ClearKey(const std::string& key) {
    states_.erase(key);
}

}  // namespace live_renderer
