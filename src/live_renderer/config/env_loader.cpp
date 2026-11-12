/**
 * Implementation of EnvLoader utility in LF Live Renderer.
 *
 * This file implements scanning and parsing of .env files.
 *
 * Usage example:
 *   live_renderer::EnvLoader::Load();
 *   std::string api_key = live_renderer::EnvLoader::Get("LFSTATS_API_KEY");
 */

#include "live_renderer/config/env_loader.hpp"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>

namespace live_renderer {

std::map<std::string, std::string> EnvLoader::env_vars_;
std::mutex EnvLoader::mutex_;

const std::vector<std::string>& EnvLoader::GetDefaultEnvPaths() {
    static const std::vector<std::string> kDefaultEnvPaths = {
        ".env",
        "../.env",
        "../../.env",
        "../../../.env"
    };
    return kDefaultEnvPaths;
}

std::string EnvLoader::Trim(const std::string& str) {
    const size_t start = str.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) {
        return "";
    }
    const size_t end = str.find_last_not_of(" \t\r\n");
    return str.substr(start, end - start + 1);
}

void EnvLoader::ParseLine(const std::string& line) {
    const std::string trimmed = Trim(line);
    if (trimmed.empty() || trimmed[0] == '#') {
        return;
    }

    const size_t equals_pos = trimmed.find('=');
    if (equals_pos == std::string::npos) {
        return;
    }

    const std::string key = Trim(trimmed.substr(0, equals_pos));
    if (key.empty()) {
        return;
    }

    std::string value = Trim(trimmed.substr(equals_pos + 1));
    if (value.size() >= 2) {
        if ((value.front() == '"' && value.back() == '"') ||
            (value.front() == '\'' && value.back() == '\'')) {
            value = value.substr(1, value.size() - 2);
        }
    }

    env_vars_[key] = value;
}

bool EnvLoader::Load(const std::string& env_path) {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<std::string> candidates;
    if (!env_path.empty()) {
        candidates.push_back(env_path);
    } else {
        for (const auto& path : GetDefaultEnvPaths()) {
            candidates.push_back(path);
        }
    }

    for (const auto& candidate : candidates) {
        std::filesystem::path p(candidate);
        if (std::filesystem::exists(p) && std::filesystem::is_regular_file(p)) {
            std::ifstream file(p);
            if (file.is_open()) {
                std::string line;
                while (std::getline(file, line)) {
                    ParseLine(line);
                }
                return true;
            }
        }
    }

    return false;
}

std::string EnvLoader::Get(
    const std::string& key,
    const std::string& default_value) {
    std::lock_guard<std::mutex> lock(mutex_);

    const auto it = env_vars_.find(key);
    if (it != env_vars_.end() && !it->second.empty()) {
        return it->second;
    }

    const char* env_val = std::getenv(key.c_str());
    if (env_val != nullptr && env_val[0] != '\0') {
        return std::string(env_val);
    }

    return default_value;
}

bool EnvLoader::Has(const std::string& key) {
    return !Get(key).empty();
}

void EnvLoader::Set(const std::string& key, const std::string& value) {
    std::lock_guard<std::mutex> lock(mutex_);
    env_vars_[key] = value;
}

void EnvLoader::Clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    env_vars_.clear();
}

}  // namespace live_renderer

