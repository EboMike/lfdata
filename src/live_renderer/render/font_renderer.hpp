#ifndef LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_
#define LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_

#include <cstdint>
#include <string>
#include "live_renderer/render/render_batch.hpp"

namespace live_renderer {

/**
 * @brief 2D OpenGL text and glyph renderer supporting outlines and rapid fire effects.
 *
 * Employs a built-in bitmap glyph texture atlas to render scaled, anti-aliased,
 * aligned text strings with optional black outlines and animated scanlines.
 */
class FontRenderer {
public:
    FontRenderer() = default;
    ~FontRenderer();

    /**
     * @brief Renders an individual text render command onto the currently active OpenGL context.
     *
     * @param cmd RenderCommand containing text string, bounds, font size, color, alignment.
     * @param current_time_ms Current wall clock milliseconds (used for rapid-fire animation).
     */
    void RenderText(const RenderCommand& cmd, int64_t current_time_ms = 0);

private:
    void EnsureTextureInitialized();
    void DrawStringQuads(
        const std::string& text,
        float x,
        float y,
        float font_size_px,
        const float color_rgba[4]);

    void DrawRapidFireEffect(
        const std::array<float, 4>& pixel_rect,
        const float base_color_rgba[4],
        int64_t current_time_ms);

    unsigned int font_texture_id_ = 0;
    bool texture_initialized_ = false;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_

