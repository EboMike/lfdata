/**
 * @file window_manager.cpp
 * @brief Implementation of WindowManager for visualization window instances.
 */

#include "live_renderer/windows/window_manager.hpp"
#include <SDL_opengl.h>
#include <algorithm>
#include <iostream>
#include "live_renderer/windows/ui_editor_window.hpp"

namespace live_renderer {

WindowManager::WindowManager(
    const UIConfig& ui_config,
    SDL_GLContext shared_gl_context,
    PreferencesManager* preferences_manager)
    : ui_config_(ui_config),
      shared_gl_context_(shared_gl_context),
      preferences_manager_(preferences_manager),
      font_renderer_(std::make_unique<FontRenderer>()) {
    SyncWithConfig(ui_config_);
}

WindowManager::~WindowManager() {
    for (auto& instance : instances_) {
        DestroyWindowInstance(instance);
    }
    instances_.clear();
    windows_.clear();
}

void WindowManager::CreateWindowInstance(
    const WindowConfig& config,
    const UIConfig& ui_config) {
    int x = config.rect[0];
    int y = config.rect[1];
    int w = std::max(100, config.rect[2]);
    int h = std::max(100, config.rect[3]);

    const WindowPreference* pref = nullptr;
    if (preferences_manager_) {
        pref = preferences_manager_->GetWindowPreference(config.id);
    }

    if (pref) {
        x = pref->x;
        y = pref->y;
        w = std::max(100, pref->width);
        h = std::max(100, pref->height);

        int target_display = preferences_manager_->ResolveDisplayIndex(
            pref->display_index, pref->display_name);
        if (target_display >= 0) {
            SDL_Rect display_bounds;
            if (SDL_GetDisplayBounds(target_display, &display_bounds) == 0) {
                if (x < display_bounds.x || x >= display_bounds.x + display_bounds.w ||
                    y < display_bounds.y || y >= display_bounds.y + display_bounds.h) {
                    x = display_bounds.x + 50;
                    y = display_bounds.y + 50;
                }
            }
        }
    } else {
        // Fallback to WindowConfig monitor_id if specified
        if (config.monitor_id >= 0 && config.monitor_id < SDL_GetNumVideoDisplays()) {
            SDL_Rect display_bounds;
            if (SDL_GetDisplayBounds(config.monitor_id, &display_bounds) == 0) {
                x = display_bounds.x + config.rect[0];
                y = display_bounds.y + config.rect[1];
            }
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

    if (preferences_manager_ && !pref) {
        preferences_manager_->CaptureWindow(config.id, sdl_win);
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
    instance.is_minimized = false;

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

SDL_Window* WindowManager::GetSdlWindow(size_t index) const {
    if (index >= instances_.size()) return nullptr;
    return instances_[index].sdl_window;
}

bool WindowManager::IsWindowMinimized(size_t index) const {
    if (index >= instances_.size()) return false;
    const auto& inst = instances_[index];
    if (!inst.sdl_window) return inst.is_minimized;
    Uint32 flags = SDL_GetWindowFlags(inst.sdl_window);
    return inst.is_minimized || ((flags & SDL_WINDOW_MINIMIZED) != 0);
}

void WindowManager::MinimizeWindow(size_t index) {
    if (index >= instances_.size()) return;
    auto& inst = instances_[index];
    if (inst.sdl_window) {
        SDL_MinimizeWindow(inst.sdl_window);
    }
    inst.is_minimized = true;
}

void WindowManager::RestoreWindow(size_t index) {
    if (index >= instances_.size()) return;
    auto& inst = instances_[index];
    if (inst.sdl_window) {
        SDL_RestoreWindow(inst.sdl_window);
    }
    inst.is_minimized = false;
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
        windows_.push_back(std::make_unique<VisualizationWindow>(
            inst.vis_window->GetConfig(), ui_config));
    }
}

bool WindowManager::HandleEvent(
    const SDL_Event& event,
    bool is_editor_mode,
    UIEditorWindow* editor_window) {
    // 1. In UI Editor Mode, handle mouse interactions for the active visualization window
    if (is_editor_mode && editor_window && !editor_window->IsEditingTemplate()) {
        int active_idx = editor_window->GetActiveWindowIndex();
        if (active_idx >= 0 && active_idx < static_cast<int>(instances_.size())) {
            auto& active_inst = instances_[active_idx];
            if (active_inst.sdl_window) {
                Uint32 active_win_id = SDL_GetWindowID(active_inst.sdl_window);
                Uint32 event_win_id = 0;
                if (event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP) {
                    event_win_id = event.button.windowID;
                } else if (event.type == SDL_MOUSEMOTION) {
                    event_win_id = event.motion.windowID;
                }

                if (event_win_id == active_win_id) {
                    int sel_idx = editor_window->GetSelectedElementIndex();
                    int win_w = active_inst.vis_window->GetWidth();
                    int win_h = active_inst.vis_window->GetHeight();
                    auto& elements = editor_window->GetActiveElements();

                    bool handled = editor_interaction_.HandleSdlEvent(
                        event, win_w, win_h, elements, sel_idx);
                    if (handled) {
                        editor_window->SetSelectedElementIndex(sel_idx);
                        active_inst.vis_window->SetConfig(ui_config_.windows[active_idx]);
                        return true;
                    }
                }
            }
        }
    }

    if (event.type != SDL_WINDOWEVENT) {
        return false;
    }

    for (auto& inst : instances_) {
        if (!inst.sdl_window || SDL_GetWindowID(inst.sdl_window) != event.window.windowID) {
            continue;
        }

        switch (event.window.event) {
            case SDL_WINDOWEVENT_CLOSE:
                // Intercept close request and minimize window instead
                SDL_MinimizeWindow(inst.sdl_window);
                inst.is_minimized = true;
                return true;

            case SDL_WINDOWEVENT_MINIMIZED:
                inst.is_minimized = true;
                return true;

            case SDL_WINDOWEVENT_RESTORED:
                inst.is_minimized = false;
                return true;

            case SDL_WINDOWEVENT_MOVED:
                if (!inst.is_minimized && preferences_manager_) {
                    preferences_manager_->CaptureWindow(inst.id, inst.sdl_window);
                }
                return true;

            case SDL_WINDOWEVENT_RESIZED:
            case SDL_WINDOWEVENT_SIZE_CHANGED:
                inst.vis_window->SetDimensions(event.window.data1, event.window.data2);
                if (!inst.is_minimized && preferences_manager_) {
                    preferences_manager_->CaptureWindow(inst.id, inst.sdl_window);
                }
                return true;

            default:
                break;
        }
    }
    return false;
}

void WindowManager::RenderWindowBatch(
    const WindowInstance& instance,
    const RenderBatch& batch,
    int64_t current_time_ms) {
    int w = 0;
    int h = 0;
    SDL_GL_GetDrawableSize(instance.sdl_window, &w, &h);
    glViewport(0, 0, w, h);

    glClearColor(
        batch.background_color[0],
        batch.background_color[1],
        batch.background_color[2],
        batch.background_color[3]);
    glClear(GL_COLOR_BUFFER_BIT);

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
        } else if (cmd.type == RenderCommand::Type::Text) {
            if (font_renderer_) {
                font_renderer_->RenderText(cmd, current_time_ms);
            }
        }
    }

    SDL_GL_SwapWindow(instance.sdl_window);
}

void WindowManager::RenderAllWindows(
    const GameStateSnapshot& state,
    bool is_editor_mode,
    int active_editor_window_index,
    int active_editor_template_id,
    int selected_element_index) {
    const int64_t now_ms = static_cast<int64_t>(SDL_GetTicks());

    for (size_t i = 0; i < instances_.size(); ++i) {
        auto& inst = instances_[i];
        if (!inst.sdl_window) continue;

        Uint32 flags = SDL_GetWindowFlags(inst.sdl_window);
        bool minimized = inst.is_minimized || ((flags & SDL_WINDOW_MINIMIZED) != 0);

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
            if (!minimized) {
                SDL_ShowWindow(inst.sdl_window);
            }

            // Sync config in editor mode to reflect live property edits
            if (i < ui_config_.windows.size()) {
                inst.vis_window->SetConfig(ui_config_.windows[i]);
            }
        } else {
            // Normal mode: show window if it was hidden, but don't unminimize
            if (!minimized && (flags & SDL_WINDOW_HIDDEN)) {
                SDL_ShowWindow(inst.sdl_window);
            }
        }

        if (minimized) {
            continue;
        }

        SDL_GLContext ctx = inst.gl_context ? inst.gl_context : shared_gl_context_;
        if (ctx) {
            SDL_GL_MakeCurrent(inst.sdl_window, ctx);
            const int highlight_elem = (is_editor_mode && static_cast<int>(i) == active_editor_window_index)
                ? selected_element_index
                : -1;
            RenderBatch batch = inst.vis_window->GenerateBatch(state, now_ms, highlight_elem);
            RenderWindowBatch(inst, batch, now_ms);
        }
    }
}

}  // namespace live_renderer
