#ifndef LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_
#define LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_

#include <string>
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Serializer and deserializer for GlobalConfig and UIConfig YAML files.
 */
class ConfigSerializer {
public:
    static bool LoadGlobalConfig(const std::string& path, GlobalConfig& out_config);
    static bool SaveGlobalConfig(const std::string& path, const GlobalConfig& config);

    static bool LoadUIConfig(const std::string& path, UIConfig& out_config);
    static bool SaveUIConfig(const std::string& path, const UIConfig& config);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_CONFIG_SERIALIZER_HPP_

