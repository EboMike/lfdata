#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <SDL_opengl.h>
#include <imgui.h>
#include <imgui_impl_opengl3.h>
#include <imgui_impl_sdl2.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <iostream>
#include <string>
#include <thread>

#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/state/mock_game_state.hpp"
#include "live_renderer/windows/main_control_window.hpp"
#include "live_renderer/windows/ui_editor_window.hpp"
#include "live_renderer/windows/window_manager.hpp"

namespace {
std::atomic<bool> g_shutdown_requested{false};

void SignalHandler(int) {
    g_shutdown_requested.store(true);
}
}  // namespace

int main(int argc, char* argv[]) {
    std::signal(SIGINT, SignalHandler);
    std::signal(SIGTERM, SignalHandler);

    std::string config_path = "live_renderer_config.yaml";
    int max_frames = -1;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) {
            config_path = argv[++i];
        } else if (arg == "--max-frames" && i + 1 < argc) {
            max_frames = std::stoi(argv[++i]);
        }
    }

    live_renderer::GlobalConfig global_cfg;
    if (!live_renderer::ConfigSerializer::LoadGlobalConfig(config_path, global_cfg)) {
        std::cout << "[live_renderer] Warning: Could not load " << config_path
                  << ", generating default config.\n";
        live_renderer::ConfigSerializer::SaveGlobalConfig(config_path, global_cfg);
    }

    live_renderer::UIConfig ui_cfg;
    if (!live_renderer::ConfigSerializer::LoadUIConfig(global_cfg.ui_config_file, ui_cfg)) {
        std::cout << "[live_renderer] Warning: Could not load " << global_cfg.ui_config_file
                  << ", creating default UI layout.\n";
        live_renderer::ConfigSerializer::SaveUIConfig(global_cfg.ui_config_file, ui_cfg);
    }

    live_renderer::LiveStateStore state_store;
    live_renderer::ProtocolParser parser(state_store);
    live_renderer::TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);
    live_renderer::MainControlWindow control_window(
        config_path, global_cfg, ui_cfg, state_store, client);
    live_renderer::UIEditorWindow editor_window(ui_cfg, global_cfg.ui_config_file);

    SDL_SetMainReady();
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) != 0) {
        std::cerr << "[live_renderer] SDL_Init Error: " << SDL_GetError() << "\n";
        return 1;
    }

    // OpenGL 3.3 Core context attributes
    const char* glsl_version = "#version 330";
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8);

    SDL_WindowFlags window_flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    SDL_Window* main_window = SDL_CreateWindow(
        "LF Live Renderer - Control",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        420,
        280,
        window_flags);
    if (!main_window) {
        std::cerr << "[live_renderer] SDL_CreateWindow Error: " << SDL_GetError() << "\n";
        SDL_Quit();
        return 1;
    }

    SDL_GLContext gl_context = SDL_GL_CreateContext(main_window);
    if (!gl_context) {
        std::cerr << "[live_renderer] SDL_GL_CreateContext Error: " << SDL_GetError() << "\n";
        SDL_DestroyWindow(main_window);
        SDL_Quit();
        return 1;
    }

    SDL_GL_MakeCurrent(main_window, gl_context);
    SDL_GL_SetSwapInterval(1);  // Enable vsync

    // Initialize Dear ImGui
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = nullptr;  // Manage layout via YAML configuration

    ImGui::StyleColorsDark();
    ImGui_ImplSDL2_InitForOpenGL(main_window, gl_context);
    ImGui_ImplOpenGL3_Init(glsl_version);

    // Initialize all visualization windows from UI config on startup
    live_renderer::WindowManager window_manager(ui_cfg, gl_context);

    control_window.SetCallbacks({
        .on_reconnect = []() {},
        .on_enter_ui_editor = []() {},
        .on_open_configuration = [&](const std::string&) {
            editor_window.SetUIConfigFile(global_cfg.ui_config_file);
            window_manager.SyncWithConfig(ui_cfg);
        },
        .on_save_settings = [&](const live_renderer::GlobalConfig&) {
            editor_window.SetUIConfigFile(global_cfg.ui_config_file);
            window_manager.SyncWithConfig(ui_cfg);
        }
    });

    editor_window.SetCallbacks({
        .on_save_and_back = [&]() {
            control_window.SetUIEditorMode(false);
            window_manager.SyncWithConfig(ui_cfg);
        },
        .on_active_window_changed = [](int) {},
        .on_active_template_changed = [](int) {}
    });

    std::cout << "[live_renderer] Connecting to lflive at " << global_cfg.host << ":"
              << global_cfg.port << "...\n";
    client.Start();

    int frame_count = 0;
    while (!g_shutdown_requested.load() && !control_window.IsQuitConfirmed()) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            ImGui_ImplSDL2_ProcessEvent(&event);
            window_manager.HandleEvent(event);
            if (event.type == SDL_QUIT) {
                control_window.ClickQuit();
            } else if (
                event.type == SDL_WINDOWEVENT &&
                event.window.event == SDL_WINDOWEVENT_CLOSE &&
                event.window.windowID == SDL_GetWindowID(main_window)) {
                control_window.ClickQuit();
            }
        }

        // Render all visualization windows with current game state (or mock state when in editor without session)
        live_renderer::GameStateSnapshot current_state = state_store.GetSnapshot();
        if (control_window.IsInUIEditorMode() && !current_state.in_session) {
            current_state = live_renderer::MockGameState::CreateMockSM5State();
        }

        window_manager.RenderAllWindows(
            current_state,
            control_window.IsInUIEditorMode(),
            editor_window.GetActiveWindowIndex(),
            editor_window.GetSelectedTemplateId());

        // Make control window context current before ImGui rendering
        SDL_GL_MakeCurrent(main_window, gl_context);

        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplSDL2_NewFrame();
        ImGui::NewFrame();

        if (control_window.IsInUIEditorMode()) {
            editor_window.RenderImGui();
        } else {
            control_window.RenderImGui();
        }

        ImGui::Render();
        int display_w = 0;
        int display_h = 0;
        SDL_GL_GetDrawableSize(main_window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        glClearColor(0.10f, 0.11f, 0.13f, 1.00f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        SDL_GL_SwapWindow(main_window);

        if (max_frames > 0 && ++frame_count >= max_frames) {
            break;
        }
    }

    std::cout << "[live_renderer] Shutting down...\n";
    client.Stop();

    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplSDL2_Shutdown();
    ImGui::DestroyContext();

    SDL_GL_DeleteContext(gl_context);
    SDL_DestroyWindow(main_window);
    SDL_Quit();
    return 0;
}
