/**
 * @file global_config.hpp
 * @brief Global configuration parameters for the live_renderer application.
 */

#ifndef LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_
#define LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_

#include <string>

namespace live_renderer {

constexpr const char* kDefaultProfilePictureAsset = "assets/default_player.png";

constexpr const char* kDefaultProfilePictureUrl =
    "https://lfstats-modern-images.s3.us-west-1.amazonaws.com/8c3b3ffc-85f7-49aa-a6a0-78ce8b0f658f";

/**
 * @brief Global configuration parameters for the live_renderer application.
 *
 * Holds connection target for the lflive TCP consumer port, the path
 * to the UI layout configuration file, the path to local preferences, and
 * the default fallback URL for player profile pictures.
 */
struct GlobalConfig {
    std::string host = "127.0.0.1";
    int port = 8001;
    std::string ui_config_file = "ui_layout.yaml";
    std::string preferences_file = "preferences.yaml";
    std::string default_profile_picture_url = kDefaultProfilePictureUrl;

    bool operator==(const GlobalConfig& other) const = default;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_
