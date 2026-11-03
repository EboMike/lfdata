#ifndef LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_
#define LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_

#include <memory>
#include <vector>
#include <unordered_map>
#include <SDL.h>
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/render/font_renderer.hpp"
#include "live_renderer/state/game_state_snapshot.hpp"
#include "live_renderer/windows/visualization_window.hpp"

namespace live_renderer {

/**
 * @brief Manages the creation, monitor positioning, persistence, and OpenGL rendering
 *        of all configured visualization windows.
 */
class WindowManager {
public:
    WindowManager(const UIConfig& ui_config, SDL_GLContext shared_gl_context);
    ~WindowManager();

    void SyncWithConfig(const UIConfig& ui_config);
    void RenderAllWindows(
        const GameStateSnapshot& state,
        bool is_editor_mode,
        int active_editor_window_index,
        int active_editor_template_id,
        int selected_element_index = -1);

    size_t GetWindowCount() const { return windows_.size(); }
    const std::vector<std::unique_ptr<VisualizationWindow>>& GetWindows() const { return windows_; }
    VisualizationWindow* GetWindow(size_t index) const;

    bool HandleEvent(const SDL_Event& event);

private:
    struct WindowInstance {
        int id = 0;
        SDL_Window* sdl_window = nullptr;
        SDL_GLContext gl_context = nullptr;
        std::unique_ptr<VisualizationWindow> vis_window;
    };

    void CreateWindowInstance(const WindowConfig& config, const UIConfig& ui_config);
    void DestroyWindowInstance(WindowInstance& instance);
    void RenderWindowBatch(
        const WindowInstance& instance,
        const RenderBatch& batch,
        int64_t current_time_ms = 0);

    const UIConfig& ui_config_;
    SDL_GLContext shared_gl_context_ = nullptr;
    std::vector<WindowInstance> instances_;
    std::vector<std::unique_ptr<VisualizationWindow>> windows_;
    std::unique_ptr<FontRenderer> font_renderer_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_

