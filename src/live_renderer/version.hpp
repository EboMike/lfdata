#ifndef LIVE_RENDERER_VERSION_HPP_
#define LIVE_RENDERER_VERSION_HPP_

/**
 * Application version definition for LF Live Renderer.
 *
 * This header defines the single source of truth for the LF Live Renderer
 * version string. Every update to the live renderer must increment this
 * version number so developers and users can easily verify that a newly
 * built executable is running.
 *
 * Example:
 *   std::cout << live_renderer::kLiveRendererVersion << std::endl;
 */

namespace live_renderer {

constexpr const char* kLiveRendererVersion = "0.1.25";

}  // namespace live_renderer

#endif  // LIVE_RENDERER_VERSION_HPP_

