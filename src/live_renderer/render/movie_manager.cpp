/**
 * @file movie_manager.cpp
 * @brief Implementation of MovieManager for looped movie playback.
 */

#include "live_renderer/render/movie_manager.hpp"
#include "live_renderer/render/texture_fit.hpp"
#include "stb_image.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>

namespace live_renderer {

MovieManager::~MovieManager() {
    UnloadAll();
}

void MovieManager::UnloadAll() {
    for (auto& [path, clip_ptr] : cache_) {
        if (clip_ptr && clip_ptr->texture_id != 0) {
            glDeleteTextures(1, &clip_ptr->texture_id);
            clip_ptr->texture_id = 0;
        }
    }
    cache_.clear();
}

std::string MovieManager::ResolveAssetPath(
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

bool MovieManager::LoadGifClip(
    const std::string& resolved_path, MovieClip& out_clip) {
    std::ifstream file(resolved_path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        return false;
    }
    std::streamsize size = file.tellg();
    if (size <= 0) {
        return false;
    }
    file.seekg(0, std::ios::beg);
    std::vector<uint8_t> buffer(size);
    if (!file.read(reinterpret_cast<char*>(buffer.data()), size)) {
        return false;
    }

    int* delays = nullptr;
    int w = 0;
    int h = 0;
    int z = 0;
    int comp = 0;
    stbi_uc* data = stbi_load_gif_from_memory(
        buffer.data(),
        static_cast<int>(buffer.size()),
        &delays,
        &w,
        &h,
        &z,
        &comp,
        4);
    if (!data || z <= 0 || w <= 0 || h <= 0) {
        if (delays) free(delays);
        if (data) stbi_image_free(data);
        return false;
    }

    out_clip.width = w;
    out_clip.height = h;
    int64_t running_time_ms = 0;
    const size_t frame_bytes = static_cast<size_t>(w) * h * 4;
    for (int i = 0; i < z; ++i) {
        MovieFrame frame;
        frame.start_ms = running_time_ms;
        const int64_t dur_ms = (delays && delays[i] > 0) ? delays[i] * 10 : 100;
        frame.duration_ms = dur_ms;
        running_time_ms += dur_ms;
        frame.rgba_bytes.assign(
            data + i * frame_bytes,
            data + (i + 1) * frame_bytes);
        out_clip.frames.push_back(std::move(frame));
    }
    out_clip.total_duration_ms = running_time_ms;

    if (delays) free(delays);
    stbi_image_free(data);
    return true;
}

bool MovieManager::LoadClip(
    const std::string& resolved_path, MovieClip& out_clip) {
    if (LoadGifClip(resolved_path, out_clip)) {
        return true;
    }

    // Fallback: load as single image frame
    int w = 0;
    int h = 0;
    int comp = 0;
    stbi_uc* data = stbi_load(resolved_path.c_str(), &w, &h, &comp, 4);
    if (!data || w <= 0 || h <= 0) {
        return false;
    }

    out_clip.width = w;
    out_clip.height = h;
    MovieFrame frame;
    frame.start_ms = 0;
    frame.duration_ms = 1000;
    const size_t frame_bytes = static_cast<size_t>(w) * h * 4;
    frame.rgba_bytes.assign(data, data + frame_bytes);
    out_clip.frames.push_back(std::move(frame));
    out_clip.total_duration_ms = 1000;

    stbi_image_free(data);
    return true;
}

void MovieManager::UpdateClipPlayback(
    MovieClip& clip,
    int64_t current_time_ms,
    float playback_speed) {
    if (clip.frames.empty() || clip.total_duration_ms <= 0) {
        return;
    }

    const float speed = std::max(0.01f, playback_speed);
    if (clip.last_time_ms < 0) {
        clip.last_time_ms = current_time_ms;
        clip.playback_clock_ms = 0.0;
    } else {
        const int64_t delta_ms = current_time_ms - clip.last_time_ms;
        if (delta_ms > 0 && delta_ms < 2000) {
            clip.playback_clock_ms += delta_ms * static_cast<double>(speed);
        }
        clip.last_time_ms = current_time_ms;
    }

    double looped_ms = std::fmod(
        clip.playback_clock_ms,
        static_cast<double>(clip.total_duration_ms));
    if (looped_ms < 0.0) {
        looped_ms += clip.total_duration_ms;
    }

    int target_frame = 0;
    for (size_t i = 0; i < clip.frames.size(); ++i) {
        const auto& f = clip.frames[i];
        if (looped_ms >= f.start_ms &&
            looped_ms < (f.start_ms + f.duration_ms)) {
            target_frame = static_cast<int>(i);
            break;
        }
    }

    if (target_frame != clip.active_frame_index || clip.texture_id == 0) {
        UploadActiveFrame(clip, target_frame);
    }
}

void MovieManager::UploadActiveFrame(MovieClip& clip, int frame_index) {
    if (frame_index < 0 ||
        frame_index >= static_cast<int>(clip.frames.size())) {
        return;
    }
    const auto& frame = clip.frames[frame_index];
    if (frame.rgba_bytes.empty()) {
        return;
    }

    if (clip.texture_id == 0) {
        glGenTextures(1, &clip.texture_id);
        glBindTexture(GL_TEXTURE_2D, clip.texture_id);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            clip.width,
            clip.height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            frame.rgba_bytes.data());
        glBindTexture(GL_TEXTURE_2D, 0);
    } else {
        glBindTexture(GL_TEXTURE_2D, clip.texture_id);
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            clip.width,
            clip.height,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            frame.rgba_bytes.data());
        glBindTexture(GL_TEXTURE_2D, 0);
    }
    clip.active_frame_index = frame_index;
}

MovieFrameInfo MovieManager::GetCurrentFrame(
    const std::string& asset_path,
    int64_t current_time_ms,
    float playback_speed) {
    MovieFrameInfo info;
    if (asset_path.empty()) {
        return info;
    }

    auto it = cache_.find(asset_path);
    if (it == cache_.end()) {
        std::string resolved = ResolveAssetPath(asset_path);
        auto new_clip = std::make_unique<MovieClip>();
        new_clip->path = asset_path;
        if (LoadClip(resolved, *new_clip)) {
            cache_[asset_path] = std::move(new_clip);
            it = cache_.find(asset_path);
        } else {
            cache_[asset_path] = nullptr;
            return info;
        }
    }

    if (!it->second) {
        return info;
    }

    MovieClip& clip = *it->second;
    UpdateClipPlayback(clip, current_time_ms, playback_speed);

    info.texture_id = clip.texture_id;
    info.width = clip.width;
    info.height = clip.height;
    info.frame_index = clip.active_frame_index;
    info.timestamp_ms = current_time_ms;
    return info;
}

bool MovieManager::GetMovieDimensions(
    const std::string& asset_path, int& out_width, int& out_height) {
    if (asset_path.empty()) return false;
    MovieFrameInfo frame = GetCurrentFrame(asset_path, 0, 1.0f);
    if (frame.width > 0 && frame.height > 0) {
        out_width = frame.width;
        out_height = frame.height;
        return true;
    }
    return false;
}

void MovieManager::RenderMovieQuad(
    const RenderCommand& cmd,
    int64_t current_time_ms) {
    MovieFrameInfo frame = GetCurrentFrame(
        cmd.texture_asset, current_time_ms, cmd.playback_speed);

    TextureFitResult fit_res = TextureFit::Compute(
        cmd.pixel_rect, frame.width, frame.height, cmd.fit);

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

    if (frame.texture_id != 0) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, frame.texture_id);
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
        glColor4f(0.3f, 0.5f, 0.7f, alpha * 0.6f);
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

bool MovieManager::RegisterSyntheticClip(
    const std::string& clip_id,
    int width,
    int height,
    const std::vector<int64_t>& frame_durations_ms,
    const std::vector<std::vector<uint8_t>>& frames_rgba) {
    if (clip_id.empty() || width <= 0 || height <= 0) {
        return false;
    }
    if (frame_durations_ms.size() != frames_rgba.size() ||
        frame_durations_ms.empty()) {
        return false;
    }

    auto clip = std::make_unique<MovieClip>();
    clip->path = clip_id;
    clip->width = width;
    clip->height = height;

    int64_t total_dur = 0;
    for (size_t i = 0; i < frame_durations_ms.size(); ++i) {
        MovieFrame frame;
        frame.start_ms = total_dur;
        frame.duration_ms = frame_durations_ms[i];
        total_dur += frame.duration_ms;
        frame.rgba_bytes = frames_rgba[i];
        clip->frames.push_back(std::move(frame));
    }
    clip->total_duration_ms = total_dur;

    cache_[clip_id] = std::move(clip);
    return true;
}

}  // namespace live_renderer

