/**
 * @file local_preferences.cpp
 * @brief Implementation of helper methods on LocalPreferences.
 */

#include "live_renderer/config/local_preferences.hpp"

namespace live_renderer {

const WindowPreference* LocalPreferences::FindWindowPreference(int window_id) const {
    for (const auto& w : windows) {
        if (w.window_id == window_id) {
            return &w;
        }
    }
    return nullptr;
}

void LocalPreferences::SetWindowPreference(const WindowPreference& pref) {
    for (auto& w : windows) {
        if (w.window_id == pref.window_id) {
            w = pref;
            return;
        }
    }
    windows.push_back(pref);
}

}  // namespace live_renderer

