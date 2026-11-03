/**
 * @file preferences_manager.hpp
 * @brief Manages loading, saving, querying, and applying local user preferences.
 *
 * Coordinates reading and persisting local preferences such as window
 * bounds (position, size) and target display monitors for visualization
 * windows and the main control window.
 *
 * Usage example:
 * @code
 * live_renderer::PreferencesManager pref_mgr("preferences.yaml");
 * pref_mgr.Load();
 * pref_mgr.ApplyToWindow(1, sdl_win);
 * pref_mgr.CaptureWindow(1, sdl_win);
 * @endcode
 */

#ifndef LIVE_RENDERER_CONFIG_PREFERENCES_MANAGER_HPP_
#define LIVE_RENDERER_CONFIG_PREFERENCES_MANAGER_HPP_

#include <string>
#include <SDL.h>
#include "live_renderer/config/local_preferences.hpp"

namespace live_renderer {

/**
 * @brief Manages local preferences persistence and window geometry queries.
 *
 * Encapsulates serialization to YAML and provides convenient methods
 * to capture window geometry and display monitors from SDL windows,
 * and apply saved preferences to SDL windows.
 */
class PreferencesManager {
public:
    /**
     * @brief Constructs a PreferencesManager targeting a specific file path.
     *
     * Initializes the manager with the given preferences file path.
     *
     * @param preferences_path File system path to the preferences YAML file.
     */
    explicit PreferencesManager(std::string preferences_path = "preferences.yaml");

    /**
     * @brief Loads preferences from the configured file path.
     *
     * Reads window preferences and display assignments from YAML.
     *
     * @return True if loaded successfully, false otherwise.
     */
    bool Load();

    /**
     * @brief Saves current preferences to the configured file path.
     *
     * Serializes all window preferences and display assignments to YAML.
     *
     * @return True if saved successfully, false on error.
     */
    bool Save();

    /**
     * @brief Returns a const reference to the current local preferences.
     *
     * Allows inspection of the loaded preferences.
     *
     * @return Const reference to LocalPreferences.
     */
    const LocalPreferences& GetPreferences() const { return preferences_; }

    /**
     * @brief Returns a mutable reference to the current local preferences.
     *
     * Allows modification of the local preferences.
     *
     * @return Mutable reference to LocalPreferences.
     */
    LocalPreferences& GetPreferences() { return preferences_; }

    /**
     * @brief Replaces current local preferences in memory.
     *
     * Assigns new preferences to the manager.
     *
     * @param prefs New preferences to assign.
     */
    void SetPreferences(const LocalPreferences& prefs) { preferences_ = prefs; }

    /**
     * @brief Gets the file path used for preferences persistence.
     *
     * Returns the currently configured YAML file path.
     *
     * @return File system path string.
     */
    const std::string& GetPath() const { return preferences_path_; }

    /**
     * @brief Sets the file path used for preferences persistence.
     *
     * Updates the destination path for subsequent Load/Save operations.
     *
     * @param path File system path string.
     */
    void SetPath(const std::string& path) { preferences_path_ = path; }

    /**
     * @brief Finds the preference for a specific visualization window ID.
     *
     * Looks up the window entry by numerical ID.
     *
     * @param window_id Numerical identifier of the window.
     * @return Pointer to WindowPreference if found, nullptr otherwise.
     */
    const WindowPreference* GetWindowPreference(int window_id) const;

    /**
     * @brief Adds or updates a window preference directly.
     *
     * Updates the in-memory preference and optionally persists to disk.
     *
     * @param pref Preference data to update.
     * @param auto_save True to automatically save to file.
     */
    void UpdateWindowPreference(const WindowPreference& pref, bool auto_save = true);

    /**
     * @brief Captures position, size, and display device from an SDL window.
     *
     * Queries SDL window geometry and associated display monitor device,
     * updating the preference for the given window ID.
     *
     * @param window_id Numerical ID of the visualization window.
     * @param window Pointer to the active SDL window.
     * @param auto_save True to automatically save to file.
     */
    void CaptureWindow(int window_id, SDL_Window* window, bool auto_save = true);

    /**
     * @brief Captures position, size, and display device for the main window.
     *
     * Queries SDL window geometry and associated display monitor device,
     * updating the main_control_window preference.
     *
     * @param window Pointer to the active SDL main window.
     * @param auto_save True to automatically save to file.
     */
    void CaptureMainWindow(SDL_Window* window, bool auto_save = true);

    /**
     * @brief Applies stored position, size, and display to an SDL window.
     *
     * Repositions and resizes the given SDL window according to stored
     * preferences, verifying monitor availability.
     *
     * @param window_id Numerical ID of the visualization window.
     * @param window Pointer to the active SDL window.
     */
    void ApplyToWindow(int window_id, SDL_Window* window) const;

    /**
     * @brief Applies stored position, size, and display to the main window.
     *
     * Repositions and resizes the main control window according to stored
     * preferences, verifying monitor availability.
     *
     * @param window Pointer to the active SDL main window.
     */
    void ApplyToMainWindow(SDL_Window* window) const;

    /**
     * @brief Resolves a target display index given preferred index and name.
     *
     * Matches the display name against currently connected video displays,
     * falling back to the display index if the name does not match.
     *
     * @param display_index Preferred index of the display monitor.
     * @param display_name Preferred device name of the display monitor.
     * @return Valid display index >= 0, or -1 if no matching display is found.
     */
    int ResolveDisplayIndex(
        int display_index,
        const std::string& display_name) const;

private:
    std::string preferences_path_;
    LocalPreferences preferences_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_PREFERENCES_MANAGER_HPP_

