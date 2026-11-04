#include "live_renderer/components/game_timer_element.hpp"
#include <iomanip>
#include <sstream>

namespace live_renderer {

std::string GameTimerElement::FormatRemainingTime(
    const GameStateSnapshot& state,
    int64_t current_steady_ms) {
    if (!state.in_session &&
        state.latest_event_time_ms <= 0 &&
        state.game_start_time_local_ms <= 0) {
        int m = state.max_game_length_seconds / 60;
        int s = state.max_game_length_seconds % 60;
        std::ostringstream oss;
        oss << std::setfill('0') << std::setw(2) << m << ":"
            << std::setfill('0') << std::setw(2) << s;
        return oss.str();
    }

    int64_t elapsed_ms = 0;
    if (state.game_over) {
        // Freeze countdown when game is over
        elapsed_ms = (state.latest_event_time_ms > 0)
            ? state.latest_event_time_ms
            : static_cast<int64_t>(state.max_game_length_seconds) * 1000;
    } else {
        auto now = std::chrono::steady_clock::now().time_since_epoch();
        int64_t steady_now =
            std::chrono::duration_cast<std::chrono::milliseconds>(now).count();

        if (current_steady_ms <= 0 ||
            (state.game_start_time_local_ms > 1000000 &&
             current_steady_ms < 1000000)) {
            current_steady_ms = steady_now;
        }

        if (state.game_start_time_local_ms > 0) {
            int64_t clock_elapsed =
                current_steady_ms - state.game_start_time_local_ms;
            if (clock_elapsed < 0) clock_elapsed = 0;
            elapsed_ms = std::max(state.latest_event_time_ms, clock_elapsed);
        } else if (state.latest_event_time_ms > 0) {
            elapsed_ms = state.latest_event_time_ms;
        }
    }

    int64_t total_game_ms =
        static_cast<int64_t>(state.max_game_length_seconds) * 1000;
    int64_t remaining_ms = total_game_ms - elapsed_ms;
    if (remaining_ms < 0) remaining_ms = 0;

    int remaining_sec = static_cast<int>((remaining_ms + 999) / 1000);
    int minutes = remaining_sec / 60;
    int seconds = remaining_sec % 60;

    std::ostringstream oss;
    oss << std::setfill('0') << std::setw(2) << minutes << ":"
        << std::setfill('0') << std::setw(2) << seconds;
    return oss.str();
}

}  // namespace live_renderer

