#ifndef LIVE_RENDERER_CONFIG_UI_CONFIG_HPP_
#define LIVE_RENDERER_CONFIG_UI_CONFIG_HPP_

#include <string>
#include <vector>
#include <array>
#include <optional>

namespace live_renderer {

/**
 * @brief Representation of an individual render element inside a template or window.
 */
struct ElementConfig {
    std::string type;                             // "user_text", "game_timer", "player_name", etc.
    std::array<float, 4> rect{0.0f, 0.0f, 1.0f, 1.0f}; // [x, y, width, height] relative (0.0 to 1.0)
    int z_position = 0;                           // Z-order: higher renders on top
    std::string text;                             // For user_text or placeholder strings
    std::string color = "#ffffff";                // Hex color string (#RRGGBB or #RRGGBBAA)
    float font_size = 20.0f;                      // Relative font size (20 = 1/40th of 800px)
    std::string alignment = "left";               // "left", "center", "right"
    std::string image_file;                       // Path to image asset
    float opacity = 1.0f;                         // 0.0 to 1.0
    float tilt = 10.0f;                           // Event scroller tilt degrees
    std::string orientation = "vertical";         // For lists: "horizontal" or "vertical"
    std::string sort_order = "ranking";           // "ranking" or "index"
    bool add_totals = false;                      // Add dummy player totals row
    int team_index = -1;                          // Target team index (-1 for all/unbound)
    int row_template_id = -1;                     // Template ID for scorecard row
    int header_template_id = -1;                  // Template ID for scorecard header row
    int player_profile_template_id = -1;          // Template ID for player profile
};

/**
 * @brief Template definition representing a reusable list of elements.
 */
struct TemplateConfig {
    int id = 0;
    std::string name;
    std::string type;                             // "scorecard_row", "scorecard_header_row", "player_profile"
    std::array<float, 2> size{1.0f, 0.05f};       // [relative width, relative height]
    std::vector<ElementConfig> elements;
};

/**
 * @brief Window layout configuration for a single rendering window.
 */
struct WindowConfig {
    int id = 0;
    std::string title;
    std::array<int, 4> rect{100, 100, 1280, 720}; // [x, y, width, height] in screen pixels
    int monitor_id = -1;                          // Preferred monitor (-1 for default/unspecified)
    std::vector<ElementConfig> elements;
};

/**
 * @brief Complete UI configuration containing all templates and visualization windows.
 */
struct UIConfig {
    std::vector<TemplateConfig> templates;
    std::vector<WindowConfig> windows;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_CONFIG_UI_CONFIG_HPP_

