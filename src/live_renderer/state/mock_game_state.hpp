#ifndef LIVE_RENDERER_STATE_MOCK_GAME_STATE_HPP_
#define LIVE_RENDERER_STATE_MOCK_GAME_STATE_HPP_

#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Factory providing realistic sample SM5 and Laserball states for UI Editor preview.
 */
class MockGameState {
public:
    static GameStateSnapshot CreateMockSM5State();
    static GameStateSnapshot CreateMockLaserballState();
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_STATE_MOCK_GAME_STATE_HPP_

