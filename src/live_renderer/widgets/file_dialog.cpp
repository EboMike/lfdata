/**
 * @file file_dialog.cpp
 * @brief Implementation of native OS file dialog wrapper.
 */

#include "live_renderer/widgets/file_dialog.hpp"
#include <cstring>
#include <filesystem>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commdlg.h>
#endif

namespace live_renderer {

bool FileDialog::IsSupported() {
#if defined(_WIN32)
    return true;
#else
    return false;
#endif
}

bool FileDialog::IsValidPath(
    const std::string& path_str,
    const std::string& base_dir) {
    if (path_str.empty()) return true;

    namespace fs = std::filesystem;
    std::error_code ec;

    if (fs::exists(path_str, ec) && !ec) {
        return true;
    }

    if (!base_dir.empty()) {
        fs::path bp = fs::path(base_dir) / path_str;
        if (fs::exists(bp, ec) && !ec) {
            return true;
        }
    }

    fs::path p(path_str);
    if (p.is_relative()) {
        auto cur = fs::current_path(ec);
        if (!ec) {
            fs::path cp = cur / p;
            if (fs::exists(cp, ec) && !ec) {
                return true;
            }
        }
    }

    if (fs::exists("../" + path_str, ec) && !ec) {
        return true;
    }
    if (fs::exists("../../" + path_str, ec) && !ec) {
        return true;
    }

    return false;
}

std::string FileDialog::NormalizePath(
    const std::string& path_str,
    const std::string& base_dir) {
    if (path_str.empty()) return "";
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path p(path_str);

    // 1. If base_dir provided, remove full path if within base_dir
    if (!base_dir.empty()) {
        fs::path base(base_dir);
        auto rel = fs::relative(p, base, ec);
        if (!ec && !rel.empty() && !rel.string().starts_with("..")) {
            return rel.generic_string();
        }
    }

    // 2. Remove full path if within current working directory
    auto cur = fs::current_path(ec);
    if (!ec) {
        auto rel = fs::relative(p, cur, ec);
        if (!ec && !rel.empty() && !rel.string().starts_with("..")) {
            return rel.generic_string();
        }
    }

    return p.generic_string();
}

std::string FileDialog::ShowOpenFileDialog(
    const char* title,
    const char* filter,
    const std::string& default_path) {
#if defined(_WIN32)
    char file_buf[MAX_PATH] = {0};
    char current_dir[MAX_PATH] = {0};
    GetCurrentDirectoryA(MAX_PATH, current_dir);

    if (!default_path.empty()) {
        std::strncpy(file_buf, default_path.c_str(), sizeof(file_buf) - 1);
    }

    OPENFILENAMEA ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = nullptr;
    ofn.lpstrFile = file_buf;
    ofn.nMaxFile = sizeof(file_buf);
    ofn.lpstrFilter = filter;
    ofn.nFilterIndex = 1;
    ofn.lpstrTitle = title;
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST | OFN_NOCHANGEDIR;

    const BOOL ok = GetOpenFileNameA(&ofn);
    SetCurrentDirectoryA(current_dir);
    if (ok) {
        return NormalizePath(file_buf);
    }
    return "";
#else
    (void)title;
    (void)filter;
    (void)default_path;
    return "";
#endif
}

std::string FileDialog::ShowOpenImageDialog(const std::string& default_path) {
    static const char kFilter[] =
        "Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.tga)\0"
        "*.png;*.jpg;*.jpeg;*.bmp;*.tga\0"
        "All Files (*.*)\0*.*\0";
    return ShowOpenFileDialog("Select Image File", kFilter, default_path);
}

std::string FileDialog::ShowOpenMovieDialog(const std::string& default_path) {
    static const char kFilter[] =
        "Video Files (*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm)\0"
        "*.mp4;*.mkv;*.avi;*.mov;*.wmv;*.flv;*.webm\0"
        "All Files (*.*)\0*.*\0";
    return ShowOpenFileDialog("Select Video File", kFilter, default_path);
}

std::string FileDialog::ShowOpenYamlDialog(const std::string& default_path) {
    static const char kFilter[] =
        "YAML Configuration (*.yaml;*.yml)\0"
        "*.yaml;*.yml\0"
        "All Files (*.*)\0*.*\0";
    return ShowOpenFileDialog(
        "Select YAML Configuration", kFilter, default_path);
}

}  // namespace live_renderer

