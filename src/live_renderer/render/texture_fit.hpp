/**
 * @file texture_fit.hpp
 * @brief Sizing mode and UV mapping calculations for image and movie frames.
 *
 * Provides aspect ratio preservation and UV calculation for stretch, scale,
 * and crop fit modes.
 *
 * Usage:
 *   auto result = TextureFit::Compute(container_rect, tex_w, tex_h, "scale");
 */

#ifndef LIVE_RENDERER_RENDER_TEXTURE_FIT_HPP_
#define LIVE_RENDERER_RENDER_TEXTURE_FIT_HPP_

#include <array>
#include <string>

namespace live_renderer {

/**
 * @brief Fit mode for image and movie rendering.
 */
enum class TextureFitMode {
    Stretch,
    Scale,
    Crop
};

/**
 * @brief Result of a texture fit calculation.
 */
struct TextureFitResult {
    // Screen pixel coordinates [x, y, w, h]
    std::array<float, 4> pixel_rect{0.0f, 0.0f, 0.0f, 0.0f};
    // Texture UV coordinates [u0, v0, u1, v1]
    std::array<float, 4> uv_rect{0.0f, 0.0f, 1.0f, 1.0f};
};

/**
 * @brief Sizing and UV mapping helper for textures and movies.
 *
 * Single responsibility: Calculates target drawing rectangle and UV bounds
 * based on container size, asset aspect ratio, and fit mode.
 */
class TextureFit {
 public:
    /**
     * @brief Parses a fit mode string into TextureFitMode enum.
     *
     * @param mode_str String such as "scale", "crop", or "stretch".
     * @return TextureFitMode Parsed enum (defaults to Stretch if unknown).
     */
    static TextureFitMode ParseFitMode(const std::string& mode_str);

    /**
     * @brief Converts TextureFitMode enum into a lowercase string.
     *
     * @param mode Fit mode enum.
     * @return std::string "stretch", "scale", or "crop".
     */
    static std::string FitModeToString(TextureFitMode mode);

    /**
     * @brief Computes geometry and UV coordinates for the specified mode.
     *
     * @param container_rect Bounding box [x, y, w, h] in screen pixels.
     * @param tex_w Texture pixel width.
     * @param tex_h Texture pixel height.
     * @param mode Fit mode enum (Stretch, Scale, Crop).
     * @return TextureFitResult Computed pixel_rect and uv_rect.
     */
    static TextureFitResult Compute(
        const std::array<float, 4>& container_rect,
        int tex_w,
        int tex_h,
        TextureFitMode mode);

    /**
     * @brief Computes geometry and UV coordinates from a string fit mode.
     *
     * @param container_rect Bounding box [x, y, w, h] in screen pixels.
     * @param tex_w Texture pixel width.
     * @param tex_h Texture pixel height.
     * @param fit_mode String "stretch", "scale", or "crop".
     * @return TextureFitResult Computed pixel_rect and uv_rect.
     */
    static TextureFitResult Compute(
        const std::array<float, 4>& container_rect,
        int tex_w,
        int tex_h,
        const std::string& fit_mode);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_TEXTURE_FIT_HPP_

