/**
 * @file texture_manager.cpp
 * @brief Implementation of TextureManager for 2D OpenGL texture management.
 */

#include "live_renderer/render/texture_manager.hpp"
#include "live_renderer/render/texture_fit.hpp"

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include <cmath>
#include <filesystem>
#include <iostream>

namespace live_renderer {

TextureManager::~TextureManager() {
    UnloadAll();
}

void TextureManager::UnloadAll() {
    for (auto& [path, info] : cache_) {
        if (info.texture_id != 0) {
            glDeleteTextures(1, &info.texture_id);
            info.texture_id = 0;
        }
    }
    cache_.clear();
}

std::string TextureManager::ResolveAssetPath(
    const std::string& asset_path) const {
    if (asset_path.empty()) return "";
    namespace fs = std::filesystem;

    if (fs::exists(asset_path)) {
        return asset_path;
    }

    std::string candidate = "../" + asset_path;
    if (fs::exists(candidate)) {
        return candidate;
    }

    candidate = "../../" + asset_path;
    if (fs::exists(candidate)) {
        return candidate;
    }

    return asset_path;
}

bool TextureManager::LoadTextureFromFile(
    const std::string& resolved_path, TextureInfo& out_info) {
    int w = 0;
    int h = 0;
    int channels = 0;
    unsigned char* data = stbi_load(
        resolved_path.c_str(), &w, &h, &channels, 4);
    if (!data) {
        return false;
    }

    GLuint tex_id = 0;
    glGenTextures(1, &tex_id);
    glBindTexture(GL_TEXTURE_2D, tex_id);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        w,
        h,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        data);
    glBindTexture(GL_TEXTURE_2D, 0);

    stbi_image_free(data);

    out_info.texture_id = tex_id;
    out_info.width = w;
    out_info.height = h;
    return true;
}

GLuint TextureManager::GetTexture(const std::string& asset_path) {
    if (asset_path.empty()) return 0;

    auto it = cache_.find(asset_path);
    if (it != cache_.end()) {
        return it->second.texture_id;
    }

    std::string resolved = ResolveAssetPath(asset_path);
    TextureInfo info;
    if (LoadTextureFromFile(resolved, info)) {
        cache_[asset_path] = info;
        return info.texture_id;
    }

    // Cache negative result to avoid redundant disk lookups
    info.texture_id = 0;
    cache_[asset_path] = info;
    return 0;
}

bool TextureManager::GetTextureDimensions(
    const std::string& asset_path, int& out_width, int& out_height) {
    if (asset_path.empty()) return false;

    GetTexture(asset_path);
    auto it = cache_.find(asset_path);
    if (it != cache_.end() && it->second.texture_id != 0) {
        out_width = it->second.width;
        out_height = it->second.height;
        return true;
    }
    return false;
}

void TextureManager::RenderTexturedQuad(const RenderCommand& cmd) {
    GLuint tex = GetTexture(cmd.texture_asset);
    int tex_w = 0;
    int tex_h = 0;
    if (tex != 0) {
        auto it = cache_.find(cmd.texture_asset);
        if (it != cache_.end()) {
            tex_w = it->second.width;
            tex_h = it->second.height;
        }
    }

    TextureFitResult fit_res = TextureFit::Compute(
        cmd.pixel_rect, tex_w, tex_h, cmd.fit);

    const float x = fit_res.pixel_rect[0];
    const float y = fit_res.pixel_rect[1];
    const float w = fit_res.pixel_rect[2];
    const float h = fit_res.pixel_rect[3];
    const float u0 = fit_res.uv_rect[0];
    const float v0 = fit_res.uv_rect[1];
    const float u1 = fit_res.uv_rect[2];
    const float v1 = fit_res.uv_rect[3];
    const float alpha = cmd.opacity;

    const bool has_tilt = std::abs(cmd.tilt_deg) > 0.01f;
    if (has_tilt) {
        glPushMatrix();
        glTranslatef(x + w * 0.5f, y + h * 0.5f, 0.0f);
        glRotatef(cmd.tilt_deg, 0.0f, 0.0f, 1.0f);
        glTranslatef(-(x + w * 0.5f), -(y + h * 0.5f), 0.0f);
    }

    if (tex != 0) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, tex);
        glColor4f(1.0f, 1.0f, 1.0f, alpha);
        glBegin(GL_QUADS);
        glTexCoord2f(u0, v0); glVertex2f(x, y);
        glTexCoord2f(u1, v0); glVertex2f(x + w, y);
        glTexCoord2f(u1, v1); glVertex2f(x + w, y + h);
        glTexCoord2f(u0, v1); glVertex2f(x, y + h);
        glEnd();
        glBindTexture(GL_TEXTURE_2D, 0);
        glDisable(GL_TEXTURE_2D);
    } else {
        // Fallback placeholder outline quad if texture file not loaded
        glColor4f(0.4f, 0.4f, 0.4f, alpha * 0.6f);
        glBegin(GL_LINE_LOOP);
        glVertex2f(x, y);
        glVertex2f(x + w, y);
        glVertex2f(x + w, y + h);
        glVertex2f(x, y + h);
        glEnd();
    }

    if (has_tilt) {
        glPopMatrix();
    }
}

}  // namespace live_renderer

