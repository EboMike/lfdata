/**
 * @file global_config.hpp
 * @brief Global configuration parameters for the live_renderer application.
 */

#ifndef LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_
#define LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_

#include <string>

namespace live_renderer {

/**
 * @brief Global configuration parameters for the live_renderer application.
 *
 * Holds connection target for the lflive TCP consumer port, the path
 * to the UI layout configuration file, and the path to local preferences.
 */
struct GlobalConfig {
    std::string host = "127.0.0.1";
    int port = 8001;
    std::string ui_config_file = "ui_layout.yaml";
    std::string preferences_file = "preferences.yaml";

    bool operator==(const GlobalConfig& other) const = default;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_GLOBAL_CONFIG_HPP_
