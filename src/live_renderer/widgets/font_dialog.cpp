/**
 * @file font_dialog.cpp
 * @brief Implementation of native OS font dialog wrapper.
 */

#include "live_renderer/widgets/font_dialog.hpp"
#include <cstring>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commdlg.h>
#endif

namespace live_renderer {

bool FontDialog::IsSupported() {
#if defined(_WIN32)
    return true;
#else
    return false;
#endif
}

std::string FontDialog::ShowFontDialog(const std::string& current_font) {
#if defined(_WIN32)
    CHOOSEFONTA cf{};
    LOGFONTA lf{};
    std::memset(&lf, 0, sizeof(lf));
    if (!current_font.empty()) {
        std::strncpy(lf.lfFaceName, current_font.c_str(), LF_FACESIZE - 1);
    }
    cf.lStructSize = sizeof(cf);
    cf.hwndOwner = nullptr;
    cf.lpLogFont = &lf;
    cf.Flags = CF_SCREENFONTS | CF_INITTOLOGFONTSTRUCT | CF_EFFECTS;
    if (ChooseFontA(&cf)) {
        return std::string(lf.lfFaceName);
    }
    return "";
#else
    (void)current_font;
    return "";
#endif
}

}  // namespace live_renderer

