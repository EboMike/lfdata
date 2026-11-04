/**
 * @file render_geometry.hpp
 * @brief OpenGL geometry rendering for solid and textured quads with corners.
 *
 * Provides drawing routines for rectangular elements, supporting both sharp
 * corners and smoothly rounded corners using OpenGL triangle fans.
 *
 * Usage:
 *   RenderGeometry::DrawSolidQuad(pixel_rect, color_rgba, corner_radius);
 *   RenderGeometry::DrawTexturedQuad(pixel_rect, uv_rect, corner_radius);
 */

#ifndef LIVE_RENDERER_RENDER_RENDER_GEOMETRY_HPP_
#define LIVE_RENDERER_RENDER_RENDER_GEOMETRY_HPP_

#include <array>

namespace live_renderer {

/**
 * @brief Helper class for drawing solid and textured quads with corner radius.
 */
class RenderGeometry {
 public:
    /**
     * @brief Draws a solid color rectangle with optional rounded corners.
     *
     * @param pixel_rect Bounding box [x, y, w, h] in screen pixels.
     * @param color_rgba Fill color [r, g, b, a].
     * @param corner_radius Corner radius in pixels (<= 0 for sharp corners).
     */
    static void DrawSolidQuad(
        const std::array<float, 4>& pixel_rect,
        const std::array<float, 4>& color_rgba,
        float corner_radius = 0.0f);

    /**
     * @brief Draws a textured rectangle with optional rounded corners.
     *
     * Texture must already be bound and texturing enabled by the caller.
     *
     * @param pixel_rect Bounding box [x, y, w, h] in screen pixels.
     * @param uv_rect Texture coordinates [u0, v0, u1, v1].
     * @param corner_radius Corner radius in pixels (<= 0 for sharp corners).
     */
    static void DrawTexturedQuad(
        const std::array<float, 4>& pixel_rect,
        const std::array<float, 4>& uv_rect,
        float corner_radius = 0.0f);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_RENDER_GEOMETRY_HPP_

