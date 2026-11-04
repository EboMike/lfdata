/**
 * @file font_dialog.hpp
 * @brief Native OS font selection dialog wrapper.
 *
 * Provides cross-platform abstraction for invoking the OS native font chooser
 * dialog (e.g. ChooseFont on Windows) to select font face names.
 *
 * Example:
 * @code
 *   if (live_renderer::FontDialog::IsSupported()) {
 *       std::string font = live_renderer::FontDialog::ShowFontDialog("Arial");
 *   }
 * @endcode
 */

#ifndef LIVE_RENDERER_WIDGETS_FONT_DIALOG_HPP_
#define LIVE_RENDERER_WIDGETS_FONT_DIALOG_HPP_

#include <string>

namespace live_renderer {

/**
 * @brief Native font dialog invoker and platform capability detector.
 *
 * Encapsulates operating system font picker dialogs (such as Win32 ChooseFont),
 * allowing UI editors to query availability and prompt users to select fonts.
 */
class FontDialog {
public:
    FontDialog() = default;
    ~FontDialog() = default;

    /**
     * @brief Checks if the host operating system provides a native font picker.
     *
     * @return True if supported by the OS (e.g. Windows), false otherwise.
     */
    static bool IsSupported();

    /**
     * @brief Opens the native OS font selection dialog modally.
     *
     * @param current_font Optional font face name to pre-select.
     * @return Selected font face name, or empty string if cancelled.
     */
    static std::string ShowFontDialog(const std::string& current_font = "");
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WIDGETS_FONT_DIALOG_HPP_

