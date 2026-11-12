/**
 * Utility for parsing and accessing .env environment files in LF Live Renderer.
 *
 * This file provides the EnvLoader class, which scans candidate directories
 * for a .env file, parses KEY=VALUE declarations, and provides thread-safe
 * accessors for configuration settings like API keys.
 *
 * Usage example:
 *   live_renderer::EnvLoader::Load();
 *   std::string key = live_renderer::EnvLoader::Get("LFSTATS_API_KEY");
 */

#ifndef LIVE_RENDERER_CONFIG_ENV_LOADER_HPP_
#define LIVE_RENDERER_CONFIG_ENV_LOADER_HPP_

#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace live_renderer {

/**
 * Utility class for loading and retrieving key-value pairs from .env files.
 *
 * Checks candidate paths (custom path, current working directory, and parent
 * directories) to locate a .env file, parses KEY=VALUE declarations, and
 * provides thread-safe access.
 */
class EnvLoader {
public:
    /**
     * Attempts to find and load key-value pairs from a .env file.
     * @param env_path Optional specific file path to try first.
     * @return True if a .env file was found and loaded, false otherwise.
     */
    static bool Load(const std::string& env_path = "");

    /**
     * Gets value for specified key from loaded .env or process environment.
     * @param key Environment variable name.
     * @param default_value Fallback value if key is not found.
     * @return String value.
     */
    static std::string Get(
        const std::string& key,
        const std::string& default_value = "");

    /**
     * Checks if a key exists in loaded .env or process environment.
     * @param key Environment variable name.
     * @return True if key is set and non-empty.
     */
    static bool Has(const std::string& key);

    /**
     * Explicitly sets a key-value pair in the in-memory env map.
     * @param key Variable name.
     * @param value Variable value.
     */
    static void Set(const std::string& key, const std::string& value);

    /**
     * Clears all in-memory loaded values. Useful for resetting in unit tests.
     */
    static void Clear();

    /**
     * Gets default search candidate paths for locating .env.
     * @return Vector of search paths.
     */
    static const std::vector<std::string>& GetDefaultEnvPaths();

private:
    static std::string Trim(const std::string& str);
    static void ParseLine(const std::string& line);

    static std::map<std::string, std::string> env_vars_;
    static std::mutex mutex_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_ENV_LOADER_HPP_

