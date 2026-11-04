/**
 * @file texture_manager.hpp
 * @brief Header for TextureManager for 2D OpenGL texture management.
 *
 * Provides texture loading via stb_image, caching by asset path, and rendering
 * of textured quads with opacity and tilt support.
 *
 * Usage:
 *   live_renderer::TextureManager textures;
 *   textures.RenderTexturedQuad(cmd);
 */

#ifndef LIVE_RENDERER_RENDER_TEXTURE_MANAGER_HPP_
#define LIVE_RENDERER_RENDER_TEXTURE_MANAGER_HPP_

#include <SDL_opengl.h>
#include <string>
#include <unordered_map>
#include "live_renderer/render/render_batch.hpp"

namespace live_renderer {

/**
 * @brief Manages loading, caching, and OpenGL rendering of 2D image textures.
 *
 * Single responsibility: Handles lifetime and drawing of textures for textured
 * quads, supporting PNG/JPG images, opacity, and rotation tilt.
 */
class TextureManager {
 public:
    TextureManager() = default;
    ~TextureManager();

    TextureManager(const TextureManager&) = delete;
    TextureManager& operator=(const TextureManager&) = delete;

    /**
     * @brief Retrieves the OpenGL texture ID for an asset, loading if needed.
     *
     * @param asset_path Path to image file.
     * @return GLuint OpenGL texture ID, or 0 if image failed to load.
     */
    GLuint GetTexture(const std::string& asset_path);

    /**
     * @brief Retrieves loaded image dimensions.
     *
     * @param asset_path Path to image file.
     * @param out_width Receives pixel width.
     * @param out_height Receives pixel height.
     * @return bool True if image was found and dimensions retrieved.
     */
    bool GetTextureDimensions(
        const std::string& asset_path, int& out_width, int& out_height);

    /**
     * @brief Renders a TexturedQuad render command in OpenGL.
     *
     * @param cmd Render command specifying pixel_rect, texture_asset, opacity.
     */
    void RenderTexturedQuad(const RenderCommand& cmd);

    /**
     * @brief Unloads and deletes all cached OpenGL textures.
     */
    void UnloadAll();

 private:
    struct TextureInfo {
        GLuint texture_id = 0;
        int width = 0;
        int height = 0;
    };

    std::unordered_map<std::string, TextureInfo> cache_;

    std::string ResolveAssetPath(const std::string& asset_path) const;
    bool LoadTextureFromFile(
        const std::string& resolved_path, TextureInfo& out_info);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_RENDER_TEXTURE_MANAGER_HPP_

