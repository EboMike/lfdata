#include "live_renderer/components/game_timer_element.hpp"
#include <algorithm>
#include <cctype>
#include <iomanip>
#include <sstream>

namespace live_renderer {

namespace {

int64_t ComputeElapsedMs(
    const GameStateSnapshot& state,
    int64_t current_steady_ms) {
    if (!state.in_session &&
        state.latest_event_time_ms <= 0 &&
        state.game_start_time_local_ms <= 0) {
        return 0;
    }

    int64_t elapsed_ms = 0;
    if (state.game_over) {
        // Freeze timer when game is over
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

    if (elapsed_ms < 0) elapsed_ms = 0;
    return elapsed_ms;
}

}  // namespace

GameTimerMode GameTimerElement::ParseMode(const std::string& mode_str) {
    std::string lower;
    lower.reserve(mode_str.size());
    for (unsigned char ch : mode_str) {
        if (!std::isspace(ch)) {
            lower.push_back(static_cast<char>(std::tolower(ch)));
        }
    }
    if (lower == "elapsed") {
        return GameTimerMode::Elapsed;
    }
    return GameTimerMode::Remaining;
}

std::string GameTimerElement::FormatTime(
    const GameStateSnapshot& state,
    GameTimerMode mode,
    int64_t current_steady_ms) {
    const int64_t total_game_ms =
        static_cast<int64_t>(state.max_game_length_seconds) * 1000;
    int64_t elapsed_ms = ComputeElapsedMs(state, current_steady_ms);
    if (total_game_ms > 0 && elapsed_ms > total_game_ms) {
        elapsed_ms = total_game_ms;
    }

    int64_t display_ms = elapsed_ms;
    if (mode == GameTimerMode::Remaining) {
        display_ms = total_game_ms - elapsed_ms;
        if (display_ms < 0) display_ms = 0;
        if (display_ms > 0 && display_ms < 1000) {
            const int centiseconds = static_cast<int>(display_ms / 10);
            std::ostringstream oss;
            oss << "00:" << std::setfill('0') << std::setw(2) << centiseconds;
            return oss.str();
        }
    }

    const int64_t total_seconds = display_ms / 1000;
    const int minutes = static_cast<int>(total_seconds / 60);
    const int seconds = static_cast<int>(total_seconds % 60);

    std::ostringstream oss;
    oss << std::setfill('0') << std::setw(2) << minutes << ":"
        << std::setfill('0') << std::setw(2) << seconds;
    return oss.str();
}

std::string GameTimerElement::FormatRemainingTime(
    const GameStateSnapshot& state,
    int64_t current_steady_ms) {
    return FormatTime(state, GameTimerMode::Remaining, current_steady_ms);
}

}  // namespace live_renderer

