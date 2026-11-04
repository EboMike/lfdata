#ifndef LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_
#define LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_

#include <cstdint>
#include <string>
#include "live_renderer/render/render_batch.hpp"

namespace live_renderer {

/**
 * @brief 2D OpenGL text renderer supporting outlines, tilt, and rapid fire.
 *
 * Employs a built-in bitmap glyph texture atlas to render scaled, anti-aliased,
 * aligned text strings with optional black outlines and animated scanlines.
 */
class FontRenderer {
public:
    FontRenderer() = default;
    ~FontRenderer();

    /**
     * @brief Renders a text command onto the active OpenGL context.
     *
     * @param cmd RenderCommand with text, bounds, font size, alignment, tilt.
     * @param current_time_ms Wall clock milliseconds for animation effects.
     */
    void RenderText(const RenderCommand& cmd, int64_t current_time_ms = 0);

private:
    void EnsureTextureInitialized();
    void DrawStringQuads(
        const std::string& text,
        float x,
        float y,
        float font_size_px,
        const float color_rgba[4],
        float tilt_deg = 0.0f,
        const std::array<float, 4>& container_rect = {0.0f, 0.0f, 0.0f, 0.0f});

    void DrawRapidFireEffect(
        const std::array<float, 4>& pixel_rect,
        const float base_color_rgba[4],
        int64_t current_time_ms);

    unsigned int font_texture_id_ = 0;
    bool texture_initialized_ = false;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_

