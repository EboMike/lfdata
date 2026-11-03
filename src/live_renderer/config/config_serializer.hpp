/**
 * @file config_serializer.hpp
 * @brief Serializer and deserializer for GlobalConfig, UIConfig, and LocalPreferences YAML files.
 */

#ifndef LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_
#define LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_

#include <string>
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/local_preferences.hpp"
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Serializer and deserializer for configuration and preference YAML files.
 *
 * Provides static methods to load and save GlobalConfig, UIConfig, and
 * LocalPreferences to and from disk.
 */
class ConfigSerializer {
public:
    /**
     * @brief Loads global configuration from a YAML file.
     *
     * Reads server network settings, UI layout path, and preferences path.
     *
     * @param path File system path to the global config YAML file.
     * @param out_config Destination struct to populate.
     * @return True if loaded successfully, false on error.
     */
    static bool LoadGlobalConfig(
        const std::string& path,
        GlobalConfig& out_config);

    /**
     * @brief Saves global configuration to a YAML file.
     *
     * Writes server network settings, UI layout path, and preferences path.
     *
     * @param path File system path to write.
     * @param config GlobalConfig struct to serialize.
     * @return True if written successfully, false on error.
     */
    static bool SaveGlobalConfig(
        const std::string& path,
        const GlobalConfig& config);

    /**
     * @brief Loads UI layout configuration from a YAML file.
     *
     * Reads templates, elements, and window definitions.
     *
     * @param path File system path to the UI config YAML file.
     * @param out_config Destination struct to populate.
     * @return True if loaded successfully, false on error.
     */
    static bool LoadUIConfig(
        const std::string& path,
        UIConfig& out_config);

    /**
     * @brief Saves UI layout configuration to a YAML file.
     *
     * Writes templates, elements, and window definitions to YAML.
     *
     * @param path File system path to write.
     * @param config UIConfig struct to serialize.
     * @return True if written successfully, false on error.
     */
    static bool SaveUIConfig(
        const std::string& path,
        const UIConfig& config);

    /**
     * @brief Loads local preferences from a YAML file.
     *
     * Reads window positions, sizes, and display device preferences.
     *
     * @param path File system path to the preferences YAML file.
     * @param out_preferences Destination struct to populate.
     * @return True if loaded successfully, false on error.
     */
    static bool LoadPreferences(
        const std::string& path,
        LocalPreferences& out_preferences);

    /**
     * @brief Saves local preferences to a YAML file.
     *
     * Serializes window geometries and display device assignments to YAML.
     *
     * @param path File system path to write.
     * @param preferences Preferences data to serialize.
     * @return True if written successfully, false on error.
     */
    static bool SavePreferences(
        const std::string& path,
        const LocalPreferences& preferences);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_
