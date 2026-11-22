/**
 * @file latency_meter_window.cpp
 * @brief Implementation of LatencyMeterWindow.
 */

#include "live_renderer/windows/latency_meter_window.hpp"

#include <SDL_opengl.h>
#include <imgui.h>
#include <imgui_impl_opengl3.h>
#include <imgui_impl_sdl2.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <vector>

namespace live_renderer {

namespace {

constexpr int kDefaultWindowWidth = 640;
constexpr int kDefaultWindowHeight = 480;
constexpr double kTwoPi = 6.28318530717958647692;
constexpr int kAudioSampleRate = 44100;

}  // namespace

LatencyMeterWindow::LatencyMeterWindow(BeepCallback beep_callback)
    : beep_callback_(std::move(beep_callback)) {
    Reset(GetSteadyNowMs());
}

LatencyMeterWindow::~LatencyMeterWindow() {
    Close();
}

void LatencyMeterWindow::SetBeepCallback(BeepCallback callback) {
    beep_callback_ = std::move(callback);
}

int64_t LatencyMeterWindow::GetSteadyNowMs() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

void LatencyMeterWindow::PlayDefaultBeep(int frequency_hz, int duration_ms) {
    if ((SDL_WasInit(SDL_INIT_AUDIO) & SDL_INIT_AUDIO) == 0) {
        if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
            return;
        }
    }

    SDL_AudioSpec desired{};
    desired.freq = kAudioSampleRate;
    desired.format = AUDIO_S16SYS;
    desired.channels = 1;
    desired.samples = 1024;

    SDL_AudioSpec obtained{};
    static SDL_AudioDeviceID audio_dev = 0;
    if (audio_dev == 0) {
        audio_dev = SDL_OpenAudioDevice(nullptr, 0, &desired, &obtained, 0);
        if (audio_dev == 0) {
            return;
        }
        SDL_PauseAudioDevice(audio_dev, 0);
    }

    const int sample_rate = obtained.freq > 0 ? obtained.freq : kAudioSampleRate;
    const int num_samples = std::max(1, (sample_rate * duration_ms) / 1000);
    std::vector<int16_t> samples(static_cast<size_t>(num_samples));
    constexpr double kAmplitude = 16000.0;
    const int fade_samples = std::min(num_samples / 10, sample_rate / 100);

    for (int i = 0; i < num_samples; ++i) {
        double env = 1.0;
        if (fade_samples > 0) {
            if (i < fade_samples) {
                env = static_cast<double>(i) / static_cast<double>(fade_samples);
            } else if (i > num_samples - fade_samples) {
                env = static_cast<double>(num_samples - i) / static_cast<double>(fade_samples);
            }
        }
        const double t = static_cast<double>(i) / static_cast<double>(sample_rate);
        samples[static_cast<size_t>(i)] = static_cast<int16_t>(
            kAmplitude * env * std::sin(kTwoPi * static_cast<double>(frequency_hz) * t));
    }

    SDL_ClearQueuedAudio(audio_dev);
    SDL_QueueAudio(
        audio_dev,
        samples.data(),
        static_cast<Uint32>(samples.size() * sizeof(int16_t)));
}

void LatencyMeterWindow::Reset(int64_t now_ms) {
    start_time_ms_ = now_ms;
    zero_time_ms_ = 0;
    current_count_ = kCountdownSeconds;
    zero_reached_ = false;
    measured_ = false;
    measured_latency_ms_ = 0;
}

void LatencyMeterWindow::Update(int64_t now_ms) {
    if (measured_) {
        return;
    }

    const int64_t elapsed_ms = std::max<int64_t>(0, now_ms - start_time_ms_);
    const int64_t total_countdown_ms = static_cast<int64_t>(kCountdownSeconds) * 1000;

    if (elapsed_ms < total_countdown_ms) {
        current_count_ = kCountdownSeconds - static_cast<int>(elapsed_ms / 1000);
        return;
    }

    current_count_ = 0;
    if (!zero_reached_) {
        zero_reached_ = true;
        zero_time_ms_ = start_time_ms_ + total_countdown_ms;
        if (beep_callback_) {
            beep_callback_(kBeepFrequencyHz, kBeepDurationMs);
        } else {
            PlayDefaultBeep(kBeepFrequencyHz, kBeepDurationMs);
        }
    }
}

bool LatencyMeterWindow::TriggerResponse(int64_t now_ms) {
    if (!zero_reached_ || measured_) {
        return false;
    }
    measured_ = true;
    measured_latency_ms_ = std::max<int64_t>(0, now_ms - zero_time_ms_);
    return true;
}

bool LatencyMeterWindow::Open() {
    if (is_open_) {
        if (sdl_window_) {
            SDL_RaiseWindow(sdl_window_);
        }
        return true;
    }

    SDL_WindowFlags flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    sdl_window_ = SDL_CreateWindow(
        "LF Live Renderer - Latency Meter",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        kDefaultWindowWidth,
        kDefaultWindowHeight,
        flags);
    if (!sdl_window_) {
        return false;
    }

    sdl_window_id_ = SDL_GetWindowID(sdl_window_);
    gl_context_ = SDL_GL_CreateContext(sdl_window_);
    if (!gl_context_) {
        SDL_DestroyWindow(sdl_window_);
        sdl_window_ = nullptr;
        sdl_window_id_ = 0;
        return false;
    }

    SDL_GL_MakeCurrent(sdl_window_, gl_context_);
    SDL_GL_SetSwapInterval(1);

    ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
    imgui_context_ = ImGui::CreateContext();
    ImGui::SetCurrentContext(imgui_context_);
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = nullptr;
    ImGui::StyleColorsDark();
    ImGui_ImplSDL2_InitForOpenGL(sdl_window_, gl_context_);
    ImGui_ImplOpenGL3_Init("#version 330");
    ImGui::SetCurrentContext(prev_ctx);

    Reset(GetSteadyNowMs());
    is_open_ = true;
    return true;
}

void LatencyMeterWindow::Close() {
    is_open_ = false;

    if (imgui_context_) {
        ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
        ImGui::SetCurrentContext(imgui_context_);
        if (gl_context_ && sdl_window_) {
            SDL_GL_MakeCurrent(sdl_window_, gl_context_);
        }
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplSDL2_Shutdown();
        ImGui::DestroyContext(imgui_context_);
        imgui_context_ = nullptr;
        if (prev_ctx != imgui_context_) {
            ImGui::SetCurrentContext(prev_ctx);
        }
    }

    if (gl_context_) {
        SDL_GL_DeleteContext(gl_context_);
        gl_context_ = nullptr;
    }
    if (sdl_window_) {
        SDL_DestroyWindow(sdl_window_);
        sdl_window_ = nullptr;
    }
    sdl_window_id_ = 0;
}

bool LatencyMeterWindow::HandleEvent(const SDL_Event& event) {
    if (!is_open_ || !sdl_window_) {
        return false;
    }

    if (event.type == SDL_WINDOWEVENT &&
        event.window.windowID == sdl_window_id_ &&
        event.window.event == SDL_WINDOWEVENT_CLOSE) {
        Close();
        return true;
    }

    if (event.type == SDL_KEYDOWN &&
        event.key.windowID == sdl_window_id_ &&
        event.key.keysym.sym == SDLK_SPACE &&
        event.key.repeat == 0) {
        TriggerResponse(GetSteadyNowMs());
    }

    bool belongs_to_window = false;
    if (event.type == SDL_WINDOWEVENT && event.window.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEMOTION && event.motion.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP) &&
               event.button.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEWHEEL && event.wheel.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_KEYDOWN || event.type == SDL_KEYUP) &&
               event.key.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_TEXTINPUT && event.text.windowID == sdl_window_id_) {
        belongs_to_window = true;
    }

    if (belongs_to_window && imgui_context_) {
        ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
        ImGui::SetCurrentContext(imgui_context_);
        ImGui_ImplSDL2_ProcessEvent(&event);
        ImGui::SetCurrentContext(prev_ctx);
        return true;
    }

    return false;
}

void LatencyMeterWindow::Render() {
    if (!is_open_ || !sdl_window_ || !gl_context_ || !imgui_context_) {
        return;
    }

    const int64_t now_ms = GetSteadyNowMs();
    Update(now_ms);

    SDL_GL_MakeCurrent(sdl_window_, gl_context_);
    ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
    ImGui::SetCurrentContext(imgui_context_);

    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplSDL2_NewFrame();
    ImGui::NewFrame();

    const ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);

    constexpr ImGuiWindowFlags kWindowFlags =
        ImGuiWindowFlags_NoDecoration |
        ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings;

    if (ImGui::Begin("Latency Meter", nullptr, kWindowFlags)) {
        RenderContents(now_ms);
    }
    ImGui::End();

    ImGui::Render();
    int display_w = 0;
    int display_h = 0;
    SDL_GL_GetDrawableSize(sdl_window_, &display_w, &display_h);
    glViewport(0, 0, display_w, display_h);
    glClearColor(0.08f, 0.09f, 0.11f, 1.00f);
    glClear(GL_COLOR_BUFFER_BIT);
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    SDL_GL_SwapWindow(sdl_window_);

    ImGui::SetCurrentContext(prev_ctx);
}

void LatencyMeterWindow::RenderContents(int64_t now_ms) {
    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const float button_height = 40.0f;
    const float bottom_area_h = measured_
        ? 0.0f
        : (button_height + ImGui::GetStyle().ItemSpacing.y * 2.0f);
    const float display_h = std::max(80.0f, avail.y - bottom_area_h);

    char main_text[64]{};
    if (measured_) {
        std::snprintf(
            main_text,
            sizeof(main_text),
            "%lld ms",
            static_cast<long long>(measured_latency_ms_));
    } else {
        std::snprintf(main_text, sizeof(main_text), "%d", current_count_);
    }

    ImFont* font = ImGui::GetFont();
    const float base_size = ImGui::GetFontSize();
    const ImVec2 base_text_sz = ImGui::CalcTextSize(main_text);
    const float target_h = display_h * 0.78f;
    const float target_w = avail.x * 0.85f;
    const float scale_h = base_text_sz.y > 0.0f ? (target_h / base_text_sz.y) : 1.0f;
    const float scale_w = base_text_sz.x > 0.0f ? (target_w / base_text_sz.x) : 1.0f;
    const float scaled_font_size = std::max(base_size, base_size * std::min(scale_h, scale_w));

    const ImVec2 win_pos = ImGui::GetCursorScreenPos();
    const ImVec2 big_sz = font->CalcTextSizeA(scaled_font_size, FLT_MAX, 0.0f, main_text);
    const ImVec2 text_pos(
        win_pos.x + (avail.x - big_sz.x) * 0.5f,
        win_pos.y + (display_h - big_sz.y) * 0.5f);

    const ImU32 text_col = measured_
        ? IM_COL32(95, 225, 130, 255)
        : IM_COL32(240, 244, 250, 255);
    ImGui::GetWindowDrawList()->AddText(
        font,
        scaled_font_size,
        text_pos,
        text_col,
        main_text);

    if (!measured_) {
        ImGui::SetCursorPosY(ImGui::GetCursorPosY() + display_h + ImGui::GetStyle().ItemSpacing.y);
        if (ImGui::Button(
                "On 0, press space or click the button",
                ImVec2(avail.x, button_height))) {
            TriggerResponse(now_ms);
        }
    }
}

}  // namespace live_renderer
