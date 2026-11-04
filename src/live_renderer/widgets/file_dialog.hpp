/**
 * @file file_dialog.hpp
 * @brief Native OS file selection dialog wrapper.
 *
 * Provides cross-platform abstraction for invoking the OS native file open
 * dialog (e.g. GetOpenFileName on Windows) for images, videos, and YAML files.
 *
 * Example:
 * @code
 *   if (live_renderer::FileDialog::IsSupported()) {
 *       std::string file =
 *           live_renderer::FileDialog::ShowOpenImageDialog("assets/logo.png");
 *   }
 * @endcode
 */

#ifndef LIVE_RENDERER_WIDGETS_FILE_DIALOG_HPP_
#define LIVE_RENDERER_WIDGETS_FILE_DIALOG_HPP_

#include <string>

namespace live_renderer {

/**
 * @brief Native file open dialog invoker and path normalizer.
 *
 * Encapsulates operating system file picker dialogs, allowing UI editors and
 * property inspectors to prompt users to browse for assets and configs.
 */
class FileDialog {
public:
    FileDialog() = default;
    ~FileDialog() = default;

    /**
     * @brief Checks if the host operating system provides a native dialog.
     *
     * @return True if supported by the OS (e.g. Windows), false otherwise.
     */
    static bool IsSupported();

    /**
     * @brief Validates whether a given file path exists on disk.
     *
     * @param path_str File path to validate (empty string treated as valid).
     * @param base_dir Optional base/config directory to check against.
     * @return True if valid/exists or empty, false otherwise.
     */
    static bool IsValidPath(
        const std::string& path_str,
        const std::string& base_dir = "");

    /**
     * @brief Normalizes a file path to be relative with forward slashes.
     *
     * Removes full path if file is within base_dir or current working dir.
     *
     * @param path_str Absolute or relative path to normalize.
     * @param base_dir Optional base/config directory to check against.
     * @return Normalized path string with forward slashes.
     */
    static std::string NormalizePath(
        const std::string& path_str,
        const std::string& base_dir = "");

    /**
     * @brief Opens a native file dialog with custom title and filter.
     *
     * @param title Dialog window title.
     * @param filter Win32 null-separated double-null-terminated filter string.
     * @param default_path Optional initial directory or file path.
     * @return Selected normalized file path, or empty string if cancelled.
     */
    static std::string ShowOpenFileDialog(
        const char* title,
        const char* filter,
        const std::string& default_path = "");

    /**
     * @brief Opens a native file dialog for image assets.
     *
     * @param default_path Optional initial file path.
     * @return Selected normalized image path, or empty string if cancelled.
     */
    static std::string ShowOpenImageDialog(
        const std::string& default_path = "");

    /**
     * @brief Opens a native file dialog for movie/video assets.
     *
     * @param default_path Optional initial file path.
     * @return Selected normalized movie path, or empty string if cancelled.
     */
    static std::string ShowOpenMovieDialog(
        const std::string& default_path = "");

    /**
     * @brief Opens a native file dialog for YAML configuration files.
     *
     * @param default_path Optional initial file path.
     * @return Selected normalized YAML path, or empty string if cancelled.
     */
    static std::string ShowOpenYamlDialog(
        const std::string& default_path = "");
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WIDGETS_FILE_DIALOG_HPP_

