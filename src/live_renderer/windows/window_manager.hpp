/**
 * @file window_manager.hpp
 * @brief Manages visualization window instances, placement, minimization, and rendering.
 */

#ifndef LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_
#define LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_

#include <memory>
#include <vector>
#include <unordered_map>
#include <SDL.h>
#include "live_renderer/config/preferences_manager.hpp"
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
    /**
     * @brief Constructs WindowManager with UI configuration and optional preferences manager.
     *
     * Initializes window manager, loads window geometry preferences if available,
     * and creates initial visualization window instances.
     *
     * @param ui_config Reference to active UI layout configuration.
     * @param shared_gl_context Shared OpenGL context for texture/resource sharing.
     * @param preferences_manager Optional pointer to PreferencesManager for geometry persistence.
     */
    WindowManager(
        const UIConfig& ui_config,
        SDL_GLContext shared_gl_context,
        PreferencesManager* preferences_manager = nullptr);

    ~WindowManager();

    /**
     * @brief Synchronizes window instances with the latest UI configuration.
     *
     * Creates new windows, updates existing ones, and destroys removed ones.
     *
     * @param ui_config Updated UI layout configuration.
     */
    void SyncWithConfig(const UIConfig& ui_config);

    /**
     * @brief Renders all active visualization windows for the current frame.
     *
     * Iterates through visible and non-minimized windows and draws their batches.
     *
     * @param state Current game state snapshot.
     * @param is_editor_mode Whether the UI Editor mode is active.
     * @param active_editor_window_index Index of window being edited in editor mode.
     * @param active_editor_template_id Template ID being edited, or -1 if window mode.
     * @param selected_element_index Element index to highlight, or -1 for none.
     */
    void RenderAllWindows(
        const GameStateSnapshot& state,
        bool is_editor_mode,
        int active_editor_window_index,
        int active_editor_template_id,
        int selected_element_index = -1);

    /**
     * @brief Gets the number of managed visualization windows.
     *
     * @return Total count of visualization windows.
     */
    size_t GetWindowCount() const { return windows_.size(); }

    /**
     * @brief Gets the vector of VisualizationWindow pointers.
     *
     * @return Const reference to vector of VisualizationWindow unique pointers.
     */
    const std::vector<std::unique_ptr<VisualizationWindow>>& GetWindows() const {
        return windows_;
    }

    /**
     * @brief Gets a pointer to the VisualizationWindow at the given index.
     *
     * @param index Index of the window.
     * @return Pointer to VisualizationWindow or nullptr if out of range.
     */
    VisualizationWindow* GetWindow(size_t index) const;

    /**
     * @brief Gets the underlying SDL_Window pointer for a window index.
     *
     * @param index Index of the window.
     * @return Pointer to SDL_Window, or nullptr if out of range.
     */
    SDL_Window* GetSdlWindow(size_t index) const;

    /**
     * @brief Checks whether the window at the given index is minimized.
     *
     * @param index Index of the window.
     * @return True if minimized, false otherwise.
     */
    bool IsWindowMinimized(size_t index) const;

    /**
     * @brief Sets or updates the preferences manager.
     *
     * @param preferences_manager Pointer to PreferencesManager.
     */
    void SetPreferencesManager(PreferencesManager* preferences_manager) {
        preferences_manager_ = preferences_manager;
    }

    /**
     * @brief Gets the current preferences manager pointer.
     *
     * @return Pointer to PreferencesManager, or nullptr if none set.
     */
    PreferencesManager* GetPreferencesManager() const {
        return preferences_manager_;
    }

    /**
     * @brief Processes SDL window events for visualization windows.
     *
     * Intercepts close events to minimize visualization windows instead of
     * destroying them, and updates geometry preferences on move/resize.
     *
     * @param event SDL_Event to inspect and handle.
     * @return True if handled by a visualization window, false otherwise.
     */
    bool HandleEvent(const SDL_Event& event);

private:
    struct WindowInstance {
        int id = 0;
        SDL_Window* sdl_window = nullptr;
        SDL_GLContext gl_context = nullptr;
        std::unique_ptr<VisualizationWindow> vis_window;
        bool is_minimized = false;
    };

    void CreateWindowInstance(const WindowConfig& config, const UIConfig& ui_config);
    void DestroyWindowInstance(WindowInstance& instance);
    void RenderWindowBatch(
        const WindowInstance& instance,
        const RenderBatch& batch,
        int64_t current_time_ms = 0);

    const UIConfig& ui_config_;
    SDL_GLContext shared_gl_context_ = nullptr;
    PreferencesManager* preferences_manager_ = nullptr;
    std::vector<WindowInstance> instances_;
    std::vector<std::unique_ptr<VisualizationWindow>> windows_;
    std::unique_ptr<FontRenderer> font_renderer_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_WINDOW_MANAGER_HPP_
