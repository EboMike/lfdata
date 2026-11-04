#include "live_renderer/components/messages_display_tracker.hpp"
#include <algorithm>

namespace live_renderer {

const std::vector<MessageDisplaySlot> MessagesDisplayTracker::kEmptySlots;

void MessagesDisplayTracker::Update(
    const std::string& display_key,
    const std::vector<ImportantEventItem>& events,
    int num_lines,
    float display_time_s,
    float fadeout_time_s,
    int64_t current_time_ms
) {
    if (num_lines < 1) {
        num_lines = 1;
    }
    auto& state = displays_[display_key];

    if (events.empty() && !state.processed_events.empty()) {
        state.slots.clear();
        state.processed_events.clear();
    }

    if (state.slots.size() != static_cast<size_t>(num_lines)) {
        state.slots.resize(num_lines);
    }

    const int64_t display_ms = static_cast<int64_t>(display_time_s * 1000.0f);
    const int64_t fadeout_ms = static_cast<int64_t>(fadeout_time_s * 1000.0f);
    const int64_t total_lifetime_ms = display_ms + fadeout_ms;

    for (auto& slot : state.slots) {
        if (!slot.active) {
            continue;
        }
        int64_t elapsed_ms = current_time_ms - slot.start_time_ms;
        if (elapsed_ms < 0) {
            slot.opacity = 1.0f;
        } else if (elapsed_ms < display_ms) {
            slot.opacity = 1.0f;
        } else if (fadeout_ms > 0 && elapsed_ms < total_lifetime_ms) {
            float p = static_cast<float>(elapsed_ms - display_ms) /
                      static_cast<float>(fadeout_ms);
            slot.opacity = std::clamp(1.0f - p, 0.0f, 1.0f);
        } else {
            slot.active = false;
            slot.opacity = 0.0f;
        }
    }

    for (const auto& ev : events) {
        auto it = state.processed_events.find(ev.id);
        bool is_new = (it == state.processed_events.end());
        bool is_updated = (!is_new &&
            (it->second.first != ev.timestamp_ms ||
             it->second.second != ev.formatted_message));

        if (!is_new && !is_updated) {
            continue;
        }

        state.processed_events[ev.id] = {ev.timestamp_ms, ev.formatted_message};

        int existing_slot_idx = -1;
        for (size_t i = 0; i < state.slots.size(); ++i) {
            if (state.slots[i].active && state.slots[i].message_id == ev.id) {
                existing_slot_idx = static_cast<int>(i);
                break;
            }
        }

        if (existing_slot_idx >= 0) {
            state.slots[existing_slot_idx].message = ev.formatted_message;
            state.slots[existing_slot_idx].start_time_ms = current_time_ms;
            state.slots[existing_slot_idx].active = true;
            state.slots[existing_slot_idx].opacity = 1.0f;
            continue;
        }

        int target_slot_idx = -1;
        for (size_t i = 0; i < state.slots.size(); ++i) {
            if (!state.slots[i].active) {
                target_slot_idx = static_cast<int>(i);
                break;
            }
        }

        if (target_slot_idx < 0 && !state.slots.empty()) {
            size_t oldest_idx = 0;
            int64_t oldest_time = state.slots[0].start_time_ms;
            for (size_t i = 1; i < state.slots.size(); ++i) {
                if (state.slots[i].start_time_ms < oldest_time) {
                    oldest_time = state.slots[i].start_time_ms;
                    oldest_idx = i;
                }
            }
            target_slot_idx = static_cast<int>(oldest_idx);
        }

        if (target_slot_idx >= 0) {
            state.slots[target_slot_idx].active = true;
            state.slots[target_slot_idx].message_id = ev.id;
            state.slots[target_slot_idx].message = ev.formatted_message;
            state.slots[target_slot_idx].start_time_ms = current_time_ms;
            state.slots[target_slot_idx].opacity = 1.0f;
        }
    }
}

const std::vector<MessageDisplaySlot>& MessagesDisplayTracker::GetSlots(
    const std::string& display_key
) const {
    auto it = displays_.find(display_key);
    if (it != displays_.end()) {
        return it->second.slots;
    }
    return kEmptySlots;
}

void MessagesDisplayTracker::Reset() {
    displays_.clear();
}

}  // namespace live_renderer

