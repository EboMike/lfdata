/**
 * @file local_preferences.hpp
 * @brief Data structures for user and window preferences stored on the local machine.
 *
 * Provides WindowPreference and LocalPreferences structs to store and retrieve
 * window geometry (position, size) and target display devices (monitor index
 * and name) across application sessions.
 *
 * Usage example:
 * @code
 * live_renderer::LocalPreferences prefs;
 * live_renderer::WindowPreference win_pref{
 *     .window_id = 1,
 *     .x = 100, .y = 100, .width = 1280, .height = 720,
 *     .display_index = 0, .display_name = "\\\\.\\DISPLAY1"
 * };
 * prefs.SetWindowPreference(win_pref);
 * const auto* found = prefs.FindWindowPreference(1);
 * @endcode
 */

#ifndef LIVE_RENDERER_CONFIG_LOCAL_PREFERENCES_HPP_
#define LIVE_RENDERER_CONFIG_LOCAL_PREFERENCES_HPP_

#include <optional>
#include <string>
#include <vector>

namespace live_renderer {

/**
 * @brief Window placement and display preference for a single window.
 *
 * Holds the window identifier, top-left desktop coordinates, dimensions,
 * and associated display monitor device index and device name.
 */
struct WindowPreference {
    int window_id = 0;
    int x = 100;
    int y = 100;
    int width = 1280;
    int height = 720;
    int display_index = -1;
    std::string display_name;

    bool operator==(const WindowPreference& other) const = default;
};

/**
 * @brief Local user preferences persisted on the local machine.
 *
 * Maintains the geometry and display assignment for the main control window
 * and each individual visualization window.
 */
struct LocalPreferences {
    std::optional<WindowPreference> main_control_window;
    std::vector<WindowPreference> windows;

    /**
     * @brief Finds a window preference by its numerical ID.
     *
     * Searches the configured window preferences for a matching window ID.
     *
     * @param window_id Numerical ID of the window to find.
     * @return Pointer to matching WindowPreference, or nullptr if not found.
     */
    const WindowPreference* FindWindowPreference(int window_id) const;

    /**
     * @brief Adds or updates a window preference.
     *
     * If an existing preference matches the window ID, it is overwritten;
     * otherwise, the preference is appended.
     *
     * @param pref Window preference to add or update.
     */
    void SetWindowPreference(const WindowPreference& pref);

    bool operator==(const LocalPreferences& other) const = default;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_LOCAL_PREFERENCES_HPP_

