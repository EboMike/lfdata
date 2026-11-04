/**
 * @file list_animation_tracker.hpp
 * @brief Header for ListAnimationTracker for smooth list reordering animations.
 *
 * Tracks the visual positions of items in lists (scorecards, rosters)
 * over time and smoothly animates order changes with Linear or
 * Ease-in-and-ease-out curves.
 *
 * Usage:
 *   live_renderer::ListAnimationTracker tracker;
 *   float animated_y = tracker.GetAnimatedPosition(
 *       "team_1", player_id, target_y, now_ms, "ease-in-and-ease-out", 0.5f);
 */

#ifndef LIVE_RENDERER_COMPONENTS_LIST_ANIMATION_TRACKER_HPP_
#define LIVE_RENDERER_COMPONENTS_LIST_ANIMATION_TRACKER_HPP_

#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>

namespace live_renderer {

/**
 * @brief Interpolation mode for list reordering animations.
 */
enum class ListAnimationType {
    None,
    Linear,
    EaseInOut
};

/**
 * @brief Manages smooth position animations when items in a list change order.
 *
 * Single responsibility: Tracks item positions over time, evaluates transition
 * progress, and computes interpolated 1D coordinates based on easing curves.
 */
class ListAnimationTracker {
 public:
    ListAnimationTracker() = default;
    ~ListAnimationTracker() = default;

    /**
     * @brief Parses string name into ListAnimationType enum.
     *
     * @param type_name "none", "linear", "ease-in-and-ease-out".
     * @return Corresponding ListAnimationType enum value.
     */
    static ListAnimationType ParseAnimationType(std::string_view type_name);

    /**
     * @brief Formats ListAnimationType enum into canonical string name.
     *
     * @param type Enum value.
     * @return Canonical string name ("none", "linear", "ease-in-and-ease-out").
     */
    static std::string FormatAnimationType(ListAnimationType type);

    /**
     * @brief Computes animated coordinate for an item within a list.
     *
     * If the item is seen for the first time, sets its initial position without
     * animation. If target coordinate changed, animates smoothly from current
     * position to target coordinate over duration_seconds.
     *
     * @param list_id Identifier for the list element.
     * @param item_id Unique key for the item (e.g. player ID or team ID).
     * @param target_pos Destination pixel offset.
     * @param current_time_ms Current timestamp in milliseconds.
     * @param anim_type Easing mode.
     * @param duration_seconds Total animation duration in seconds.
     * @return Interpolated pixel coordinate.
     */
    float GetAnimatedPosition(
        const std::string& list_id,
        int item_id,
        float target_pos,
        int64_t current_time_ms,
        ListAnimationType anim_type,
        float duration_seconds);

    /**
     * @brief Convenience overload accepting animation type string.
     *
     * @param list_id Identifier for the list element.
     * @param item_id Unique key for the item.
     * @param target_pos Destination pixel offset.
     * @param current_time_ms Current timestamp in milliseconds.
     * @param anim_type_str "none", "linear", "ease-in-and-ease-out".
     * @param duration_seconds Animation duration in seconds.
     * @return Interpolated pixel coordinate.
     */
    float GetAnimatedPosition(
        const std::string& list_id,
        int item_id,
        float target_pos,
        int64_t current_time_ms,
        std::string_view anim_type_str,
        float duration_seconds);

    /**
     * @brief Clears all tracked positions and active transitions.
     */
    void Reset();

 private:
    struct ItemTrack {
        float current_pos = 0.0f;
        float start_pos = 0.0f;
        float target_pos = 0.0f;
        int64_t start_time_ms = 0;
        int64_t duration_ms = 0;
        ListAnimationType anim_type = ListAnimationType::None;
        bool initialized = false;
    };

    std::unordered_map<std::string, ItemTrack> tracks_;

    static std::string MakeKey(const std::string& list_id, int item_id);
    static float ComputeProgress(float t, ListAnimationType anim_type);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_LIST_ANIMATION_TRACKER_HPP_

