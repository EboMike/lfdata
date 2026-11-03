#include "live_renderer/windows/window_manager.hpp"
#include <SDL_opengl.h>
#include <algorithm>
#include <iostream>

namespace live_renderer {

WindowManager::WindowManager(const UIConfig& ui_config, SDL_GLContext shared_gl_context)
    : ui_config_(ui_config),
      shared_gl_context_(shared_gl_context) {
    SyncWithConfig(ui_config_);
}

WindowManager::~WindowManager() {
    for (auto& instance : instances_) {
        DestroyWindowInstance(instance);
    }
    instances_.clear();
    windows_.clear();
}

void WindowManager::CreateWindowInstance(const WindowConfig& config, const UIConfig& ui_config) {
    int x = config.rect[0];
    int y = config.rect[1];
    int w = std::max(100, config.rect[2]);
    int h = std::max(100, config.rect[3]);

    // Handle monitor positioning if specified
    if (config.monitor_id >= 0 && config.monitor_id < SDL_GetNumVideoDisplays()) {
        SDL_Rect display_bounds;
        if (SDL_GetDisplayBounds(config.monitor_id, &display_bounds) == 0) {
            x = display_bounds.x + config.rect[0];
            y = display_bounds.y + config.rect[1];
        }
    }

    SDL_WindowFlags flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI);

    SDL_Window* sdl_win = SDL_CreateWindow(
        config.title.c_str(),
        x,
        y,
        w,
        h,
        flags);

    if (!sdl_win) {
        std::cerr << "[WindowManager] Failed to create SDL_Window: " << SDL_GetError() << "\n";
        return;
    }

    SDL_GLContext gl_ctx = nullptr;
    if (shared_gl_context_) {
        SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT, 1);
        gl_ctx = SDL_GL_CreateContext(sdl_win);
    }

    WindowInstance instance;
    instance.id = config.id;
    instance.sdl_window = sdl_win;
    instance.gl_context = gl_ctx;
    instance.vis_window = std::make_unique<VisualizationWindow>(config, ui_config);

    windows_.push_back(std::make_unique<VisualizationWindow>(config, ui_config));
    instances_.push_back(std::move(instance));
}

void WindowManager::DestroyWindowInstance(WindowInstance& instance) {
    if (instance.gl_context) {
        SDL_GL_DeleteContext(instance.gl_context);
        instance.gl_context = nullptr;
    }
    if (instance.sdl_window) {
        SDL_DestroyWindow(instance.sdl_window);
        instance.sdl_window = nullptr;
    }
}

VisualizationWindow* WindowManager::GetWindow(size_t index) const {
    if (index >= windows_.size()) return nullptr;
    return windows_[index].get();
}

void WindowManager::SyncWithConfig(const UIConfig& ui_config) {
    std::unordered_map<int, WindowConfig> target_configs;
    for (const auto& w : ui_config.windows) {
        target_configs[w.id] = w;
    }

    // Remove windows that are no longer configured
    auto it = instances_.begin();
    while (it != instances_.end()) {
        if (!target_configs.contains(it->id)) {
            DestroyWindowInstance(*it);
            it = instances_.erase(it);
        } else {
            ++it;
        }
    }

    // Update existing or create new ones
    for (const auto& w : ui_config.windows) {
        auto existing = std::find_if(
            instances_.begin(),
            instances_.end(),
            [&w](const WindowInstance& inst) { return inst.id == w.id; });

        if (existing != instances_.end()) {
            existing->vis_window->SetConfig(w);
            SDL_SetWindowTitle(existing->sdl_window, w.title.c_str());
        } else {
            CreateWindowInstance(w, ui_config);
        }
    }

    windows_.clear();
    for (const auto& inst : instances_) {
        windows_.push_back(std::make_unique<VisualizationWindow>(inst.vis_window->GetConfig(), ui_config));
    }
}

bool WindowManager::HandleEvent(const SDL_Event& event) {
    if (event.type == SDL_WINDOWEVENT) {
        for (auto& inst : instances_) {
            if (inst.sdl_window && SDL_GetWindowID(inst.sdl_window) == event.window.windowID) {
                if (event.window.event == SDL_WINDOWEVENT_RESIZED ||
                    event.window.event == SDL_WINDOWEVENT_SIZE_CHANGED) {
                    inst.vis_window->SetDimensions(event.window.data1, event.window.data2);
                    return true;
                }
            }
        }
    }
    return false;
}

void WindowManager::RenderWindowBatch(const WindowInstance& instance, const RenderBatch& batch) {
    int w = 0, h = 0;
    SDL_GL_GetDrawableSize(instance.sdl_window, &w, &h);
    glViewport(0, 0, w, h);

    glClearColor(
        batch.background_color[0],
        batch.background_color[1],
        batch.background_color[2],
        batch.background_color[3]);
    glClear(GL_COLOR_BUFFER_BIT);

    // Simple immediate OpenGL 2D drawing pass for solid quads
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0.0, static_cast<double>(w), static_cast<double>(h), 0.0, -1.0, 1.0);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    for (const auto& cmd : batch.commands) {
        if (cmd.type == RenderCommand::Type::SolidQuad) {
            glColor4f(cmd.color_rgba[0], cmd.color_rgba[1], cmd.color_rgba[2], cmd.color_rgba[3]);
            glBegin(GL_QUADS);
            glVertex2f(cmd.pixel_rect[0], cmd.pixel_rect[1]);
            glVertex2f(cmd.pixel_rect[0] + cmd.pixel_rect[2], cmd.pixel_rect[1]);
            glVertex2f(cmd.pixel_rect[0] + cmd.pixel_rect[2], cmd.pixel_rect[1] + cmd.pixel_rect[3]);
            glVertex2f(cmd.pixel_rect[0], cmd.pixel_rect[1] + cmd.pixel_rect[3]);
            glEnd();
        }
    }

    SDL_GL_SwapWindow(instance.sdl_window);
}

void WindowManager::RenderAllWindows(
    const GameStateSnapshot& state,
    bool is_editor_mode,
    int active_editor_window_index,
    int active_editor_template_id) {
    for (size_t i = 0; i < instances_.size(); ++i) {
        auto& inst = instances_[i];
        if (!inst.sdl_window) continue;

        // In UI Editor Mode, only one window is shown at a time (or none if editing a template)
        if (is_editor_mode) {
            if (active_editor_template_id >= 0) {
                SDL_HideWindow(inst.sdl_window);
                continue;
            }
            if (static_cast<int>(i) != active_editor_window_index) {
                SDL_HideWindow(inst.sdl_window);
                continue;
            }
            SDL_ShowWindow(inst.sdl_window);
        } else {
            // Normal mode: all windows remain open
            SDL_ShowWindow(inst.sdl_window);
        }

        SDL_GLContext ctx = inst.gl_context ? inst.gl_context : shared_gl_context_;
        if (ctx) {
            SDL_GL_MakeCurrent(inst.sdl_window, ctx);
            RenderBatch batch = inst.vis_window->GenerateBatch(state);
            RenderWindowBatch(inst, batch);
        }
    }
}

}  // namespace live_renderer

