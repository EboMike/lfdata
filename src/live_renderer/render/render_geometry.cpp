/**
 * @file render_geometry.cpp
 * @brief Implementation of OpenGL quad and rounded rectangle geometry routines.
 */

#include "live_renderer/render/render_geometry.hpp"
#include <algorithm>
#include <cmath>
#include <SDL_opengl.h>

namespace live_renderer {

namespace {

constexpr int kSegmentsPerCorner = 8;
constexpr float kPi = 3.14159265358979323846f;

struct CornerInfo {
    float cx;
    float cy;
    float a0;
    float a1;
};

}  // namespace

void RenderGeometry::DrawSolidQuad(
    const std::array<float, 4>& pixel_rect,
    const std::array<float, 4>& color_rgba,
    float corner_radius) {
    const float x = pixel_rect[0];
    const float y = pixel_rect[1];
    const float w = pixel_rect[2];
    const float h = pixel_rect[3];
    if (w <= 0.0f || h <= 0.0f) {
        return;
    }

    glColor4f(
        color_rgba[0],
        color_rgba[1],
        color_rgba[2],
        color_rgba[3]);

    const float r = std::min({corner_radius, w * 0.5f, h * 0.5f});
    if (r <= 0.5f) {
        glBegin(GL_QUADS);
        glVertex2f(x, y);
        glVertex2f(x + w, y);
        glVertex2f(x + w, y + h);
        glVertex2f(x, y + h);
        glEnd();
        return;
    }

    const CornerInfo corners[4] = {
        {x + w - r, y + r, 0.0f, kPi * 0.5f},
        {x + r, y + r, kPi * 0.5f, kPi},
        {x + r, y + h - r, kPi, kPi * 1.5f},
        {x + w - r, y + h - r, kPi * 1.5f, kPi * 2.0f}
    };

    glBegin(GL_TRIANGLE_FAN);
    glVertex2f(x + w * 0.5f, y + h * 0.5f);

    for (int c = 0; c < 4; ++c) {
        for (int i = 0; i <= kSegmentsPerCorner; ++i) {
            const float t =
                static_cast<float>(i) / static_cast<float>(kSegmentsPerCorner);
            const float angle =
                corners[c].a0 + t * (corners[c].a1 - corners[c].a0);
            const float px = corners[c].cx + r * std::cos(angle);
            const float py = corners[c].cy - r * std::sin(angle);
            glVertex2f(px, py);
        }
    }
    glVertex2f(corners[0].cx + r, corners[0].cy);
    glEnd();
}

void RenderGeometry::DrawTexturedQuad(
    const std::array<float, 4>& pixel_rect,
    const std::array<float, 4>& uv_rect,
    float corner_radius) {
    const float x = pixel_rect[0];
    const float y = pixel_rect[1];
    const float w = pixel_rect[2];
    const float h = pixel_rect[3];
    if (w <= 0.0f || h <= 0.0f) {
        return;
    }

    const float u0 = uv_rect[0];
    const float v0 = uv_rect[1];
    const float u1 = uv_rect[2];
    const float v1 = uv_rect[3];

    const float r = std::min({corner_radius, w * 0.5f, h * 0.5f});
    if (r <= 0.5f) {
        glBegin(GL_QUADS);
        glTexCoord2f(u0, v0); glVertex2f(x, y);
        glTexCoord2f(u1, v0); glVertex2f(x + w, y);
        glTexCoord2f(u1, v1); glVertex2f(x + w, y + h);
        glTexCoord2f(u0, v1); glVertex2f(x, y + h);
        glEnd();
        return;
    }

    const CornerInfo corners[4] = {
        {x + w - r, y + r, 0.0f, kPi * 0.5f},
        {x + r, y + r, kPi * 0.5f, kPi},
        {x + r, y + h - r, kPi, kPi * 1.5f},
        {x + w - r, y + h - r, kPi * 1.5f, kPi * 2.0f}
    };

    glBegin(GL_TRIANGLE_FAN);
    glTexCoord2f((u0 + u1) * 0.5f, (v0 + v1) * 0.5f);
    glVertex2f(x + w * 0.5f, y + h * 0.5f);

    for (int c = 0; c < 4; ++c) {
        for (int i = 0; i <= kSegmentsPerCorner; ++i) {
            const float t =
                static_cast<float>(i) / static_cast<float>(kSegmentsPerCorner);
            const float angle =
                corners[c].a0 + t * (corners[c].a1 - corners[c].a0);
            const float px = corners[c].cx + r * std::cos(angle);
            const float py = corners[c].cy - r * std::sin(angle);
            const float u = u0 + ((px - x) / w) * (u1 - u0);
            const float v = v0 + ((py - y) / h) * (v1 - v0);
            glTexCoord2f(u, v);
            glVertex2f(px, py);
        }
    }
    const float px0 = corners[0].cx + r;
    const float py0 = corners[0].cy;
    glTexCoord2f(
        u0 + ((px0 - x) / w) * (u1 - u0),
        v0 + ((py0 - y) / h) * (v1 - v0));
    glVertex2f(px0, py0);
    glEnd();
}

}  // namespace live_renderer

