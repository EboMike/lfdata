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
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

namespace live_renderer {

namespace {

constexpr int kDefaultWindowWidth = 720;
constexpr int kDefaultWindowHeight = 640;
constexpr double kTwoPi = 6.28318530717958647692;
constexpr int kAudioSampleRate = 44100;

std::string TrimString(const std::string& s) {
    size_t start = 0;
    while (start < s.size() &&
           std::isspace(static_cast<unsigned char>(s[start]))) {
        ++start;
    }
    size_t end = s.size();
    while (end > start &&
           std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(start, end - start);
}

std::string ToLowerString(const std::string& s) {
    std::string out = s;
    for (char& ch : out) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return out;
}

void DrawCenteredScaledText(
    const char* text,
    float area_x,
    float area_y,
    float area_w,
    float area_h,
    float max_h_ratio,
    float max_w_ratio,
    ImU32 color) {
    ImFont* font = ImGui::GetFont();
    const float base_size = ImGui::GetFontSize();
    const ImVec2 base_sz = ImGui::CalcTextSize(text);
    const float target_h = area_h * max_h_ratio;
    const float target_w = area_w * max_w_ratio;
    const float scale_h = base_sz.y > 0.0f ? (target_h / base_sz.y) : 1.0f;
    const float scale_w = base_sz.x > 0.0f ? (target_w / base_sz.x) : 1.0f;
    const float scaled_size =
        std::max(base_size, base_size * std::min(scale_h, scale_w));
    const ImVec2 big_sz = font->CalcTextSizeA(scaled_size, FLT_MAX, 0.0f, text);
    const ImVec2 pos(
        area_x + (area_w - big_sz.x) * 0.5f,
        area_y + (area_h - big_sz.y) * 0.5f);
    ImGui::GetWindowDrawList()->AddText(font, scaled_size, pos, color, text);
}

}  // namespace

LatencyMeterWindow::LatencyMeterWindow(
    BeepCallback beep_callback,
    FeedReaderFactory feed_reader_factory)
    : beep_callback_(std::move(beep_callback)),
      feed_reader_factory_(std::move(feed_reader_factory)) {
    Reset(GetSteadyNowMs());
}

LatencyMeterWindow::~LatencyMeterWindow() {
    Close();
}

void LatencyMeterWindow::SetBeepCallback(BeepCallback callback) {
    beep_callback_ = std::move(callback);
}

void LatencyMeterWindow::SetFeedReaderFactory(FeedReaderFactory factory) {
    feed_reader_factory_ = std::move(factory);
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
                env = static_cast<double>(num_samples - i) /
                    static_cast<double>(fade_samples);
            }
        }
        const double t = static_cast<double>(i) / static_cast<double>(sample_rate);
        samples[static_cast<size_t>(i)] = static_cast<int16_t>(
            kAmplitude * env *
            std::sin(kTwoPi * static_cast<double>(frequency_hz) * t));
    }

    SDL_ClearQueuedAudio(audio_dev);
    SDL_QueueAudio(
        audio_dev,
        samples.data(),
        static_cast<Uint32>(samples.size() * sizeof(int16_t)));
}

std::string LatencyMeterWindow::NormalizeRtmpUrl(const std::string& input) {
    std::string trimmed = TrimString(input);
    if (trimmed.empty()) {
        return "";
    }
    const std::string lower = ToLowerString(trimmed);
    if (lower.rfind("rtmp://", 0) == 0 || lower.rfind("rtmps://", 0) == 0) {
        return trimmed;
    }
    return "rtmp://" + trimmed;
}

bool LatencyMeterWindow::IsMajorityRed(
    const std::vector<uint8_t>& rgba,
    int width,
    int height) {
    if (width <= 0 || height <= 0) {
        return false;
    }
    const size_t total_pixels =
        static_cast<size_t>(width) * static_cast<size_t>(height);
    if (rgba.size() < total_pixels * 4) {
        return false;
    }

    size_t red_count = 0;
    for (size_t i = 0; i < total_pixels; ++i) {
        const uint8_t r = rgba[i * 4 + 0];
        const uint8_t g = rgba[i * 4 + 1];
        const uint8_t b = rgba[i * 4 + 2];
        if (r >= 100 && r > static_cast<int>(g) + 40 &&
            r > static_cast<int>(b) + 40) {
            ++red_count;
        }
    }
    return red_count * 2 > total_pixels;
}

bool LatencyMeterWindow::IsMajorityGreen(
    const std::vector<uint8_t>& rgba,
    int width,
    int height) {
    if (width <= 0 || height <= 0) {
        return false;
    }
    const size_t total_pixels =
        static_cast<size_t>(width) * static_cast<size_t>(height);
    if (rgba.size() < total_pixels * 4) {
        return false;
    }

    size_t green_count = 0;
    for (size_t i = 0; i < total_pixels; ++i) {
        const uint8_t r = rgba[i * 4 + 0];
        const uint8_t g = rgba[i * 4 + 1];
        const uint8_t b = rgba[i * 4 + 2];
        if (g >= 100 && g > static_cast<int>(r) + 40 &&
            g > static_cast<int>(b) + 40) {
            ++green_count;
        }
    }
    return green_count * 2 > total_pixels;
}

void LatencyMeterWindow::ShowModeSelection() {
    ReleaseFeedResources();
    mode_ = Mode::kSelection;
    auto_phase_ = AutoPhase::kEnterAddress;
    auto_count_ = kAutoCountdownSeconds;
    rtmp_error_.clear();
    measured_ = false;
    measured_latency_ms_ = 0;
    zero_reached_ = false;
    current_count_ = kCountdownSeconds;
}

void LatencyMeterWindow::Reset(int64_t now_ms) {
    ReleaseFeedResources();
    mode_ = Mode::kManual;
    start_time_ms_ = now_ms;
    zero_time_ms_ = 0;
    current_count_ = kCountdownSeconds;
    zero_reached_ = false;
    measured_ = false;
    measured_latency_ms_ = 0;
}

void LatencyMeterWindow::StartAutomaticSetup() {
    ReleaseFeedResources();
    mode_ = Mode::kAutomatic;
    auto_phase_ = AutoPhase::kEnterAddress;
    auto_count_ = kAutoCountdownSeconds;
    auto_countdown_start_ms_ = 0;
    green_start_ms_ = 0;
    rtmp_error_.clear();
    measured_ = false;
    measured_latency_ms_ = 0;
}

bool LatencyMeterWindow::StartAutomaticFeed(
    const std::string& address_or_url,
    int64_t now_ms) {
    (void)now_ms;
    mode_ = Mode::kAutomatic;
    const std::string normalized = NormalizeRtmpUrl(address_or_url);
    if (normalized.empty()) {
        rtmp_error_ = "Please enter an RTMP IP address or URL.";
        auto_phase_ = AutoPhase::kEnterAddress;
        return false;
    }

    std::string validation_error;
    if (!RtspFeedReader::ValidateStreamUrl(normalized, true, validation_error)) {
        rtmp_error_ = validation_error;
        auto_phase_ = AutoPhase::kEnterAddress;
        return false;
    }

    ReleaseFeedResources();
    if (feed_reader_factory_) {
        feed_reader_ = feed_reader_factory_();
    } else {
        feed_reader_ = std::make_unique<RtspFeedReader>(true);
    }

    if (!feed_reader_ || !feed_reader_->Open(normalized)) {
        rtmp_error_ = feed_reader_
            ? feed_reader_->GetErrorMessage()
            : "Failed to create RTMP feed reader.";
        feed_reader_.reset();
        auto_phase_ = AutoPhase::kEnterAddress;
        return false;
    }

    rtmp_error_.clear();
    measured_ = false;
    measured_latency_ms_ = 0;
    auto_count_ = kAutoCountdownSeconds;
    auto_countdown_start_ms_ = 0;
    green_start_ms_ = 0;
    auto_phase_ = AutoPhase::kWaitingForRed;
    return true;
}

void LatencyMeterWindow::Update(int64_t now_ms) {
    if (mode_ == Mode::kManual) {
        UpdateManual(now_ms);
    } else if (mode_ == Mode::kAutomatic) {
        UpdateAutomatic(now_ms);
    }
}

void LatencyMeterWindow::UpdateManual(int64_t now_ms) {
    if (measured_) {
        return;
    }

    const int64_t elapsed_ms = std::max<int64_t>(0, now_ms - start_time_ms_);
    const int64_t total_countdown_ms =
        static_cast<int64_t>(kCountdownSeconds) * 1000;

    if (elapsed_ms < total_countdown_ms) {
        current_count_ =
            kCountdownSeconds - static_cast<int>(elapsed_ms / 1000);
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

void LatencyMeterWindow::UpdateAutomatic(int64_t now_ms) {
    if (auto_phase_ == AutoPhase::kEnterAddress ||
        auto_phase_ == AutoPhase::kMeasured) {
        return;
    }

    bool has_new_frame = false;
    if (feed_reader_) {
        has_new_frame = feed_reader_->CopyLatestFrameRgba(
            frame_rgba_, frame_width_, frame_height_, frame_seq_);
    }

    if (auto_phase_ == AutoPhase::kWaitingForRed) {
        if (has_new_frame &&
            IsMajorityRed(frame_rgba_, frame_width_, frame_height_)) {
            auto_phase_ = AutoPhase::kCountdownToGreen;
            auto_countdown_start_ms_ = now_ms;
            auto_count_ = kAutoCountdownSeconds;
        }
        return;
    }

    if (auto_phase_ == AutoPhase::kCountdownToGreen) {
        const int64_t elapsed_ms =
            std::max<int64_t>(0, now_ms - auto_countdown_start_ms_);
        const int64_t total_ms =
            static_cast<int64_t>(kAutoCountdownSeconds) * 1000;
        if (elapsed_ms < total_ms) {
            auto_count_ =
                kAutoCountdownSeconds - static_cast<int>(elapsed_ms / 1000);
            return;
        }
        auto_count_ = 0;
        auto_phase_ = AutoPhase::kWaitingForGreen;
        green_start_ms_ = now_ms;
        if (has_new_frame &&
            IsMajorityGreen(frame_rgba_, frame_width_, frame_height_)) {
            auto_phase_ = AutoPhase::kMeasured;
            measured_ = true;
            measured_latency_ms_ = 0;
        }
        return;
    }

    if (auto_phase_ == AutoPhase::kWaitingForGreen) {
        if (has_new_frame &&
            IsMajorityGreen(frame_rgba_, frame_width_, frame_height_)) {
            auto_phase_ = AutoPhase::kMeasured;
            measured_ = true;
            measured_latency_ms_ =
                std::max<int64_t>(0, now_ms - green_start_ms_);
        }
    }
}

bool LatencyMeterWindow::TriggerResponse(int64_t now_ms) {
    if (mode_ != Mode::kManual || !zero_reached_ || measured_) {
        return false;
    }
    measured_ = true;
    measured_latency_ms_ = std::max<int64_t>(0, now_ms - zero_time_ms_);
    return true;
}

void LatencyMeterWindow::ReleaseFeedResources() {
    if (feed_reader_) {
        feed_reader_->Close();
        feed_reader_.reset();
    }
    frame_rgba_.clear();
    frame_width_ = 0;
    frame_height_ = 0;
    frame_seq_ = 0;
    uploaded_seq_ = 0;

    if (feed_texture_id_ != 0 && gl_context_ && sdl_window_) {
        SDL_GL_MakeCurrent(sdl_window_, gl_context_);
        GLuint tex = static_cast<GLuint>(feed_texture_id_);
        glDeleteTextures(1, &tex);
        feed_texture_id_ = 0;
        texture_width_ = 0;
        texture_height_ = 0;
    }
}

void LatencyMeterWindow::UploadFeedTexture() {
    if (frame_seq_ == 0 || frame_seq_ == uploaded_seq_ ||
        frame_rgba_.empty() || frame_width_ <= 0 || frame_height_ <= 0) {
        return;
    }

    GLuint tex = static_cast<GLuint>(feed_texture_id_);
    if (tex == 0) {
        glGenTextures(1, &tex);
        feed_texture_id_ = static_cast<unsigned int>(tex);
    }

    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);

    if (texture_width_ != frame_width_ || texture_height_ != frame_height_) {
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            frame_width_,
            frame_height_,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            frame_rgba_.data());
        texture_width_ = frame_width_;
        texture_height_ = frame_height_;
    } else {
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            frame_width_,
            frame_height_,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            frame_rgba_.data());
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    uploaded_seq_ = frame_seq_;
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

    ShowModeSelection();
    is_open_ = true;
    return true;
}

void LatencyMeterWindow::Close() {
    is_open_ = false;
    ReleaseFeedResources();

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

    if (mode_ == Mode::kManual &&
        event.type == SDL_KEYDOWN &&
        event.key.windowID == sdl_window_id_ &&
        event.key.keysym.sym == SDLK_SPACE &&
        event.key.repeat == 0) {
        TriggerResponse(GetSteadyNowMs());
    }

    bool belongs_to_window = false;
    if (event.type == SDL_WINDOWEVENT &&
        event.window.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEMOTION &&
               event.motion.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_MOUSEBUTTONDOWN ||
                event.type == SDL_MOUSEBUTTONUP) &&
               event.button.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEWHEEL &&
               event.wheel.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_KEYDOWN || event.type == SDL_KEYUP) &&
               event.key.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_TEXTINPUT &&
               event.text.windowID == sdl_window_id_) {
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
    if (mode_ == Mode::kAutomatic &&
        (auto_phase_ == AutoPhase::kWaitingForRed ||
         auto_phase_ == AutoPhase::kCountdownToGreen ||
         auto_phase_ == AutoPhase::kWaitingForGreen)) {
        UploadFeedTexture();
    }

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
    if (mode_ == Mode::kSelection) {
        RenderSelection(now_ms);
    } else if (mode_ == Mode::kManual) {
        RenderManual(now_ms);
    } else {
        RenderAutomatic(now_ms);
    }
}

void LatencyMeterWindow::RenderSelection(int64_t now_ms) {
    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const float btn_w = std::min(300.0f, avail.x * 0.7f);
    const float btn_h = 48.0f;
    const float spacing = ImGui::GetStyle().ItemSpacing.y * 2.0f;
    const float total_h = btn_h * 2.0f + spacing;
    const float start_y = std::max(0.0f, (avail.y - total_h) * 0.5f);
    const float start_x = std::max(0.0f, (avail.x - btn_w) * 0.5f);

    ImGui::SetCursorPos(ImVec2(start_x, start_y));
    if (ImGui::Button("Automatic (RTMP)", ImVec2(btn_w, btn_h))) {
        StartAutomaticSetup();
    }

    ImGui::SetCursorPos(ImVec2(start_x, start_y + btn_h + spacing));
    if (ImGui::Button("Manual", ImVec2(btn_w, btn_h))) {
        Reset(now_ms);
    }
}

void LatencyMeterWindow::RenderMeasuredResult() {
    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const ImVec2 win_pos = ImGui::GetCursorScreenPos();
    char main_text[64]{};
    std::snprintf(
        main_text,
        sizeof(main_text),
        "%lld ms",
        static_cast<long long>(measured_latency_ms_));
    DrawCenteredScaledText(
        main_text,
        win_pos.x,
        win_pos.y,
        avail.x,
        avail.y,
        0.78f,
        0.85f,
        IM_COL32(95, 225, 130, 255));
}

void LatencyMeterWindow::RenderManual(int64_t now_ms) {
    if (measured_) {
        RenderMeasuredResult();
        return;
    }

    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const float button_height = 40.0f;
    const float bottom_area_h =
        button_height + ImGui::GetStyle().ItemSpacing.y * 2.0f;
    const float display_h = std::max(80.0f, avail.y - bottom_area_h);

    char main_text[64]{};
    std::snprintf(main_text, sizeof(main_text), "%d", current_count_);

    const ImVec2 win_pos = ImGui::GetCursorScreenPos();
    DrawCenteredScaledText(
        main_text,
        win_pos.x,
        win_pos.y,
        avail.x,
        display_h,
        0.78f,
        0.85f,
        IM_COL32(240, 244, 250, 255));

    ImGui::SetCursorPosY(
        ImGui::GetCursorPosY() + display_h + ImGui::GetStyle().ItemSpacing.y);
    if (ImGui::Button(
            "On 0, press space or click the button",
            ImVec2(avail.x, button_height))) {
        TriggerResponse(now_ms);
    }
}

void LatencyMeterWindow::RenderAutomatic(int64_t now_ms) {
    if (auto_phase_ == AutoPhase::kEnterAddress) {
        RenderAutomaticAddressEntry(now_ms);
    } else if (auto_phase_ == AutoPhase::kMeasured) {
        RenderMeasuredResult();
    } else {
        RenderAutomaticSplitView();
    }
}

void LatencyMeterWindow::RenderAutomaticAddressEntry(int64_t now_ms) {
    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const float panel_w = std::min(420.0f, avail.x * 0.85f);
    const float start_x = std::max(0.0f, (avail.x - panel_w) * 0.5f);
    const float start_y = std::max(0.0f, (avail.y - 120.0f) * 0.5f);

    ImGui::SetCursorPos(ImVec2(start_x, start_y));
    ImGui::TextUnformatted("RTMP IP Address:");

    ImGui::SetCursorPosX(start_x);
    ImGui::SetNextItemWidth(panel_w);
    const bool enter_pressed = ImGui::InputText(
        "##rtmp_address",
        rtmp_address_buf_,
        sizeof(rtmp_address_buf_),
        ImGuiInputTextFlags_EnterReturnsTrue);

    ImGui::SetCursorPosX(start_x);
    ImGui::TextDisabled("Example: rtmp://127.0.0.1:1935/live/gopro");

    ImGui::SetCursorPosX(start_x);
    if (ImGui::Button("Go", ImVec2(panel_w, 40.0f)) || enter_pressed) {
        StartAutomaticFeed(rtmp_address_buf_, now_ms);
    }

    if (!rtmp_error_.empty()) {
        ImGui::SetCursorPosX(start_x);
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.35f, 0.35f, 1.0f));
        ImGui::PushTextWrapPos(start_x + panel_w);
        ImGui::TextUnformatted(rtmp_error_.c_str());
        ImGui::PopTextWrapPos();
        ImGui::PopStyleColor();
    }
}

void LatencyMeterWindow::RenderAutomaticSplitView() {
    const ImVec2 avail = ImGui::GetContentRegionAvail();
    const ImVec2 origin = ImGui::GetCursorScreenPos();
    const float half_h = std::max(40.0f, avail.y * 0.5f);

    ImDrawList* draw_list = ImGui::GetWindowDrawList();
    const bool is_green = (auto_phase_ == AutoPhase::kWaitingForGreen);
    const ImU32 top_bg = is_green
        ? IM_COL32(0, 220, 0, 255)
        : IM_COL32(220, 0, 0, 255);

    draw_list->AddRectFilled(
        origin,
        ImVec2(origin.x + avail.x, origin.y + half_h),
        top_bg);

    if (!is_green) {
        const char* prompt =
            "Point camera to the red background and keep it there";
        DrawCenteredScaledText(
            prompt,
            origin.x,
            origin.y + half_h * 0.08f,
            avail.x,
            half_h * 0.30f,
            0.70f,
            0.90f,
            IM_COL32(255, 255, 255, 255));

        char count_buf[16]{};
        std::snprintf(count_buf, sizeof(count_buf), "%d", auto_count_);
        DrawCenteredScaledText(
            count_buf,
            origin.x,
            origin.y + half_h * 0.38f,
            avail.x,
            half_h * 0.56f,
            0.85f,
            0.80f,
            IM_COL32(255, 255, 255, 255));
    }

    const float bot_y = origin.y + half_h;
    draw_list->AddRectFilled(
        ImVec2(origin.x, bot_y),
        ImVec2(origin.x + avail.x, origin.y + avail.y),
        IM_COL32(15, 18, 22, 255));

    if (feed_texture_id_ != 0 && texture_width_ > 0 && texture_height_ > 0) {
        const float tex_aspect =
            static_cast<float>(texture_width_) /
            static_cast<float>(texture_height_);
        const float box_aspect = avail.x / half_h;
        float draw_w = avail.x;
        float draw_h = half_h;
        if (tex_aspect > box_aspect) {
            draw_h = avail.x / tex_aspect;
        } else {
            draw_w = half_h * tex_aspect;
        }
        const float img_x = origin.x + (avail.x - draw_w) * 0.5f;
        const float img_y = bot_y + (half_h - draw_h) * 0.5f;
        draw_list->AddImage(
            static_cast<ImTextureID>(feed_texture_id_),
            ImVec2(img_x, img_y),
            ImVec2(img_x + draw_w, img_y + draw_h));
    } else {
        std::string status = "Connecting to RTMP feed...";
        if (feed_reader_ &&
            feed_reader_->GetState() == FeedConnectionState::kError) {
            status = "Feed error: " + feed_reader_->GetErrorMessage();
        }
        DrawCenteredScaledText(
            status.c_str(),
            origin.x,
            bot_y,
            avail.x,
            half_h,
            0.14f,
            0.85f,
            IM_COL32(220, 220, 220, 255));
    }
}

}  // namespace live_renderer
