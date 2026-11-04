#ifndef LIVE_RENDERER_RENDER_RICH_TEXT_LAYOUT_HPP_
#define LIVE_RENDERER_RENDER_RICH_TEXT_LAYOUT_HPP_

#include <string>
#include <string_view>
#include <vector>
#include <array>
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Representation of an individual styled run of text.
 */
struct TextRun {
    std::string text;
    std::string hex_color; // e.g. "#ff0000" or empty for default
    bool is_image = false;
    std::string image_asset;
};

/**
 * @brief Utilities for resolving placeholders and parsing rich text tags.
 */
class RichTextLayout {
public:
    /**
     * @brief Resolves placeholders like {game_type} and {center}.
     */
    static std::string SubstitutePlaceholders(
        std::string_view raw_text,
        const GameStateSnapshot& state);

    /**
     * @brief Parses <font color="#RRGGBB">...</font> tags and [img:path] into styled TextRuns.
     */
    static std::vector<TextRun> ParseMarkup(
        std::string_view text,
        const std::string& default_color = "#ffffff");

    /**
     * @brief Computes font pixel height from relative font size according to design/live_renderer.md:
     *        "A font size of 20 will take up about 1/40 of the image's height of a window that is 800 pixels high."
     *        (i.e. size 20 = 20px at 800px window height -> scale = window_height / 800.0f).
     */
    static float ComputePixelFontSize(float font_size, float window_height) {
        return font_size * (window_height / 800.0f);
    }

    /**
     * @brief Computes scaled pixel vertical spacing relative to window height.
     *        A vertical spacing of 5 will take up 5px in a window that is 800
     *        pixels high, and scales proportionally with window height.
     */
    static float ComputePixelVerticalSpacing(
        float vertical_spacing, float window_height) {
        return vertical_spacing * (window_height / 800.0f);
    }
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_RICH_TEXT_LAYOUT_HPP_

