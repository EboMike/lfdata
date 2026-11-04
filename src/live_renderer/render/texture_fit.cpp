/**
 * @file texture_fit.cpp
 * @brief Implementation of TextureFit calculation helper.
 */

#include "live_renderer/render/texture_fit.hpp"
#include <algorithm>

namespace live_renderer {

TextureFitMode TextureFit::ParseFitMode(const std::string& mode_str) {
    if (mode_str == "scale" || mode_str == "Scale") {
        return TextureFitMode::Scale;
    }
    if (mode_str == "crop" || mode_str == "Crop") {
        return TextureFitMode::Crop;
    }
    return TextureFitMode::Stretch;
}

std::string TextureFit::FitModeToString(TextureFitMode mode) {
    switch (mode) {
        case TextureFitMode::Scale:
            return "scale";
        case TextureFitMode::Crop:
            return "crop";
        case TextureFitMode::Stretch:
        default:
            return "stretch";
    }
}

TextureFitResult TextureFit::Compute(
    const std::array<float, 4>& container_rect,
    int tex_w,
    int tex_h,
    TextureFitMode mode) {
    TextureFitResult result;
    result.pixel_rect = container_rect;
    result.uv_rect = {0.0f, 0.0f, 1.0f, 1.0f};

    const float cw = container_rect[2];
    const float ch = container_rect[3];
    if (tex_w <= 0 || tex_h <= 0 || cw <= 0.0f || ch <= 0.0f) {
        return result;
    }

    if (mode == TextureFitMode::Stretch) {
        return result;
    }

    const float r_tex = static_cast<float>(tex_w) / static_cast<float>(tex_h);
    const float r_rect = cw / ch;

    if (mode == TextureFitMode::Scale) {
        if (r_rect > r_tex) {
            // Container wider than texture: fit height, center horizontally
            const float scaled_w = ch * r_tex;
            const float ox = container_rect[0] + (cw - scaled_w) * 0.5f;
            result.pixel_rect = {ox, container_rect[1], scaled_w, ch};
        } else {
            // Container is taller than texture: fit to width, center vertically
            const float scaled_h = cw / r_tex;
            const float oy = container_rect[1] + (ch - scaled_h) * 0.5f;
            result.pixel_rect = {container_rect[0], oy, cw, scaled_h};
        }
        return result;
    }

    if (mode == TextureFitMode::Crop) {
        result.pixel_rect = container_rect;
        if (r_rect > r_tex) {
            // Container is wider than texture: crop vertically (top and bottom)
            const float v_fraction = r_tex / r_rect;
            const float v0 = 0.5f * (1.0f - v_fraction);
            const float v1 = 0.5f * (1.0f + v_fraction);
            result.uv_rect = {0.0f, v0, 1.0f, v1};
        } else {
            // Container taller than texture: crop width (left and right)
            const float u_fraction = r_rect / r_tex;
            const float u0 = 0.5f * (1.0f - u_fraction);
            const float u1 = 0.5f * (1.0f + u_fraction);
            result.uv_rect = {u0, 0.0f, u1, 1.0f};
        }
        return result;
    }

    return result;
}

TextureFitResult TextureFit::Compute(
    const std::array<float, 4>& container_rect,
    int tex_w,
    int tex_h,
    const std::string& fit_mode) {
    return Compute(container_rect, tex_w, tex_h, ParseFitMode(fit_mode));
}

}  // namespace live_renderer

