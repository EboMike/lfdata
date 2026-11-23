#ifndef LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_
#define LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_

#include <string>
#include <cstdint>
#include <chrono>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Display modes for the game timer element.
 */
enum class GameTimerMode {
    Remaining,  // Counts down from scheduled duration to 00:00 (SS:ss in last second)
    Elapsed,    // Counts up from 00:00
};

/**
 * @brief Logic for computing the MM:SS (or SS:ss) game timer.
 *
 * According to design/live_renderer.md:
 * Supports "remaining" (default) and "elapsed" modes. In remaining mode,
 * counts down from the scheduled game length until 00:00 (stopping early if
 * the game ends early) and switches to SS:ss (1/100th of a second) during
 * the last second.
 */
class GameTimerElement {
public:
    /**
     * @brief Parses a timer mode configuration string.
     * @param mode_str Configuration string ("remaining" or "elapsed").
     * @return Parsed GameTimerMode (defaults to Remaining).
     */
    static GameTimerMode ParseMode(const std::string& mode_str);

    /**
     * @brief Formats the game timer based on the current state and mode.
     * @param state The current GameStateSnapshot.
     * @param mode Display mode (Remaining or Elapsed).
     * @param current_steady_ms Monotonic time in milliseconds (or <= 0 to use system steady clock).
     * @return Formatted string ("MM:SS" or "SS:ss").
     */
    static std::string FormatTime(
        const GameStateSnapshot& state,
        GameTimerMode mode = GameTimerMode::Remaining,
        int64_t current_steady_ms = 0);

    /**
     * @brief Formats the countdown timer as MM:SS (or SS:ss) based on the current state.
     * @param state The current GameStateSnapshot.
     * @param current_steady_ms Monotonic time in milliseconds (or <= 0 to use system steady clock).
     * @return Formatted string ("MM:SS" or "SS:ss").
     */
    static std::string FormatRemainingTime(
        const GameStateSnapshot& state,
        int64_t current_steady_ms = 0);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_

