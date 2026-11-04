#ifndef LIVE_RENDERER_COMPONENTS_MESSAGES_DISPLAY_TRACKER_HPP_
#define LIVE_RENDERER_COMPONENTS_MESSAGES_DISPLAY_TRACKER_HPP_

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Represents an individual message display slot/line.
 */
struct MessageDisplaySlot {
    int message_id = 0;
    std::string message;
    int64_t start_time_ms = 0;
    bool active = false;
    float opacity = 0.0f;
};

/**
 * @brief Manages slots, lifetimes, and fade-out for important game messages.
 *
 * Single responsibility: Tracks a fixed number of message lines, assigns new
 * messages to the top-most inactive line, handles replacements of existing
 * message IDs, and computes fade-out opacities over time.
 */
class MessagesDisplayTracker {
 public:
    MessagesDisplayTracker() = default;
    ~MessagesDisplayTracker() = default;

    /**
     * @brief Updates tracked slots for a specific display key.
     *
     * @param display_key Unique identifier for the element instance.
     * @param events List of important events from the active game snapshot.
     * @param num_lines Number of lines allocated for messages.
     * @param display_time_s Seconds message remains fully visible.
     * @param fadeout_time_s Seconds for message to fade out linearly.
     * @param current_time_ms Current timestamp in milliseconds.
     */
    void Update(
        const std::string& display_key,
        const std::vector<ImportantEventItem>& events,
        int num_lines,
        float display_time_s,
        float fadeout_time_s,
        int64_t current_time_ms
    );

    /**
     * @brief Returns current message slots for the given display key.
     *
     * @param display_key Unique identifier for the element instance.
     * @return Const reference to vector of slots.
     */
    const std::vector<MessageDisplaySlot>& GetSlots(
        const std::string& display_key
    ) const;

    /**
     * @brief Clears all tracked displays, slots, and event records.
     */
    void Reset();

 private:
    struct DisplayState {
        std::vector<MessageDisplaySlot> slots;
        std::unordered_map<int, std::pair<int64_t, std::string>>
            processed_events;
    };

    std::unordered_map<std::string, DisplayState> displays_;
    static const std::vector<MessageDisplaySlot> kEmptySlots;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_MESSAGES_DISPLAY_TRACKER_HPP_

