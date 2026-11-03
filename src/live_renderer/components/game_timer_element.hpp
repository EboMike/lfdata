#ifndef LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_
#define LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_

#include <string>
#include <cstdint>
#include <chrono>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Logic for computing the MM:SS remaining game timer.
 *
 * According to design/live_renderer.md:
 * "The amount of time left in the game, in MM:SS. Note that this must be computed
 *  and updated by this binary. The reference point is the length of the game, and
 *  the time at which the beginning of the game was processed and visualized."
 */
class GameTimerElement {
public:
    /**
     * @brief Formats the countdown timer as MM:SS based on the current state.
     * @param state The current GameStateSnapshot.
     * @param current_steady_ms Monotonic time in milliseconds (or <= 0 to use system steady clock).
     * @return Formatted string "MM:SS".
     */
    static std::string FormatRemainingTime(
        const GameStateSnapshot& state,
        int64_t current_steady_ms = 0);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_GAME_TIMER_ELEMENT_HPP_

