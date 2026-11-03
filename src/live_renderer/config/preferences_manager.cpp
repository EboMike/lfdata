/**
 * @file preferences_manager.cpp
 * @brief Implementation of PreferencesManager.
 */

#include "live_renderer/config/preferences_manager.hpp"
#include <algorithm>
#include <iostream>
#include "live_renderer/config/config_serializer.hpp"

namespace live_renderer {

PreferencesManager::PreferencesManager(std::string preferences_path)
    : preferences_path_(std::move(preferences_path)) {}

bool PreferencesManager::Load() {
    return ConfigSerializer::LoadPreferences(preferences_path_, preferences_);
}

bool PreferencesManager::Save() {
    return ConfigSerializer::SavePreferences(preferences_path_, preferences_);
}

const WindowPreference* PreferencesManager::GetWindowPreference(int window_id) const {
    return preferences_.FindWindowPreference(window_id);
}

void PreferencesManager::UpdateWindowPreference(
    const WindowPreference& pref,
    bool auto_save) {
    preferences_.SetWindowPreference(pref);
    if (auto_save) {
        Save();
    }
}

int PreferencesManager::ResolveDisplayIndex(
    int display_index,
    const std::string& display_name) const {
    const int num_displays = SDL_GetNumVideoDisplays();
    if (num_displays <= 0) {
        return -1;
    }

    // Try matching display by device name first
    if (!display_name.empty()) {
        for (int i = 0; i < num_displays; ++i) {
            const char* name = SDL_GetDisplayName(i);
            if (name && display_name == name) {
                return i;
            }
        }
    }

    // Fallback to display index if valid
    if (display_index >= 0 && display_index < num_displays) {
        return display_index;
    }

    return -1;
}

void PreferencesManager::CaptureWindow(
    int window_id,
    SDL_Window* window,
    bool auto_save) {
    if (!window) return;

    // Do not capture geometry if the window is currently minimized,
    // as OS platforms report dummy coordinates (e.g. -32000 on Windows).
    Uint32 flags = SDL_GetWindowFlags(window);
    if (flags & SDL_WINDOW_MINIMIZED) {
        return;
    }

    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
    SDL_GetWindowPosition(window, &x, &y);
    SDL_GetWindowSize(window, &w, &h);

    int display_index = SDL_GetWindowDisplayIndex(window);
    std::string display_name;
    if (display_index >= 0 && display_index < SDL_GetNumVideoDisplays()) {
        const char* name = SDL_GetDisplayName(display_index);
        if (name) {
            display_name = name;
        }
    }

    WindowPreference pref;
    pref.window_id = window_id;
    pref.x = x;
    pref.y = y;
    pref.width = w;
    pref.height = h;
    pref.display_index = display_index;
    pref.display_name = display_name;

    preferences_.SetWindowPreference(pref);
    if (auto_save) {
        Save();
    }
}

void PreferencesManager::CaptureMainWindow(
    SDL_Window* window,
    bool auto_save) {
    if (!window) return;

    Uint32 flags = SDL_GetWindowFlags(window);
    if (flags & SDL_WINDOW_MINIMIZED) {
        return;
    }

    int x = 0;
    int y = 0;
    int w = 0;
    int h = 0;
    SDL_GetWindowPosition(window, &x, &y);
    SDL_GetWindowSize(window, &w, &h);

    int display_index = SDL_GetWindowDisplayIndex(window);
    std::string display_name;
    if (display_index >= 0 && display_index < SDL_GetNumVideoDisplays()) {
        const char* name = SDL_GetDisplayName(display_index);
        if (name) {
            display_name = name;
        }
    }

    WindowPreference pref;
    pref.window_id = 0;
    pref.x = x;
    pref.y = y;
    pref.width = w;
    pref.height = h;
    pref.display_index = display_index;
    pref.display_name = display_name;

    preferences_.main_control_window = pref;
    if (auto_save) {
        Save();
    }
}

static void ApplyPreferenceToSdlWindow(
    const PreferencesManager& mgr,
    const WindowPreference& pref,
    SDL_Window* window) {
    int target_display = mgr.ResolveDisplayIndex(
        pref.display_index, pref.display_name);

    int x = pref.x;
    int y = pref.y;

    if (target_display >= 0) {
        SDL_Rect bounds;
        if (SDL_GetDisplayBounds(target_display, &bounds) == 0) {
            if (x < bounds.x || x >= bounds.x + bounds.w ||
                y < bounds.y || y >= bounds.y + bounds.h) {
                x = bounds.x + 50;
                y = bounds.y + 50;
            }
        }
    }

    SDL_SetWindowSize(
        window,
        std::max(100, pref.width),
        std::max(100, pref.height));
    SDL_SetWindowPosition(window, x, y);
}

void PreferencesManager::ApplyToWindow(
    int window_id,
    SDL_Window* window) const {
    if (!window) return;
    const WindowPreference* pref = preferences_.FindWindowPreference(window_id);
    if (!pref) return;

    ApplyPreferenceToSdlWindow(*this, *pref, window);
}

void PreferencesManager::ApplyToMainWindow(SDL_Window* window) const {
    if (!window || !preferences_.main_control_window.has_value()) return;
    ApplyPreferenceToSdlWindow(*this, *preferences_.main_control_window, window);
}

}  // namespace live_renderer

