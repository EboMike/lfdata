/**
 * @file font_renderer.hpp
 * @brief 2D OpenGL text rendering engine supporting TrueType fonts and effects.
 */

#ifndef LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_
#define LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_

#include <array>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include "live_renderer/render/render_batch.hpp"
#include "stb_truetype.h"

namespace live_renderer {

/**
 * @brief Baked TrueType font atlas and glyph metrics.
 */
struct BakedGlyphFont {
    unsigned int texture_id = 0;
    int tex_width = 1024;
    int tex_height = 1024;
    float baked_size = 64.0f;
    float ascent = 0.0f;
    float descent = 0.0f;
    float line_gap = 0.0f;
    std::vector<stbtt_bakedchar> cdata;
    bool is_valid = false;
};

/**
 * @brief 2D OpenGL text renderer supporting TrueType fonts, outlines, tilt,
 * and rapid fire animations.
 *
 * Employs stb_truetype to rasterize fonts dynamically and maintain OpenGL
 * texture atlases. Falls back to a built-in bitmap glyph font when a requested
 * font is unavailable.
 */
class FontRenderer {
public:
    FontRenderer() = default;
    ~FontRenderer();

    /**
     * @brief Sets the global default font name.
     *
     * @param font_name Font face name or asset path.
     */
    void SetDefaultFont(const std::string& font_name);

    /**
     * @brief Gets the current default font name.
     *
     * @return Current default font face or filename.
     */
    const std::string& GetDefaultFont() const { return default_font_; }

    /**
     * @brief Resolves a font face name or path to a filesystem path.
     *
     * @param font_name Font face name (e.g. "Arial") or filename.
     * @return Valid filesystem path if found, or empty string.
     */
    static std::string ResolveFontPath(const std::string& font_name);

    /**
     * @brief Measures the pixel width of a rendered text string.
     *
     * @param text Text string to measure.
     * @param font_name Font face name or filename.
     * @param font_size_px Desired font height in pixels.
     * @return Measured pixel width.
     */
    float MeasureTextWidth(
        const std::string& text,
        const std::string& font_name,
        float font_size_px);

    /**
     * @brief Renders a text command onto the active OpenGL context.
     *
     * @param cmd RenderCommand with text, bounds, font, font size, tilt, etc.
     * @param current_time_ms Wall clock milliseconds for animation effects.
     */
    void RenderText(const RenderCommand& cmd, int64_t current_time_ms = 0);

private:
    BakedGlyphFont* GetOrLoadFont(const std::string& font_name);
    void EnsureFallbackTextureInitialized();

    void DrawStringQuadsTTF(
        const BakedGlyphFont& font,
        const std::string& text,
        float x,
        float y,
        float font_size_px,
        const float color_rgba[4],
        float tilt_deg = 0.0f,
        const std::array<float, 4>& container_rect = {0.0f, 0.0f, 0.0f, 0.0f});

    void DrawStringQuadsFallback(
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

    std::string default_font_ = "default";
    unsigned int fallback_texture_id_ = 0;
    bool fallback_initialized_ = false;
    std::unordered_map<std::string, BakedGlyphFont> font_cache_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_FONT_RENDERER_HPP_
