#ifndef LIVE_RENDERER_RENDER_RENDER_BATCH_HPP_
#define LIVE_RENDERER_RENDER_RENDER_BATCH_HPP_

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace live_renderer {

/**
 * @brief Representation of an individual 2D draw command emitted by window elements.
 */
struct RenderCommand {
    enum class Type {
        Text,
        SolidQuad,
        TexturedQuad
    };

    Type type = Type::Text;
    // Bounding rectangle in absolute screen pixel coordinates [x, y, w, h]
    std::array<float, 4> pixel_rect{0.0f, 0.0f, 0.0f, 0.0f};

    // Text properties
    std::string text;
    std::string hex_color = "#ffffff";
    float font_size_px = 20.0f;
    std::string alignment = "left"; // "left", "center", "right"
    bool black_outline = true;

    // Image / Texture properties
    std::string texture_asset;
    float opacity = 1.0f;
    std::array<float, 4> color_rgba{1.0f, 1.0f, 1.0f, 1.0f};
};

/**
 * @brief Holds an ordered list of 2D draw commands for a single rendering frame.
 */
struct RenderBatch {
    int window_width = 1280;
    int window_height = 720;
    std::array<float, 4> background_color{0.08f, 0.09f, 0.11f, 1.0f};
    std::vector<RenderCommand> commands;

    void Clear() {
        commands.clear();
    }
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_RENDER_BATCH_HPP_

