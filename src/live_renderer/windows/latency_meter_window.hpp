/**
 * @file latency_meter_window.hpp
 * @brief Separate window for latency settings and manual/automatic RTMP measurement.
 *
 * Shows the current latency in milliseconds with immediate text-field
 * adjustment, plus "Automatic latency (RTMP)" and "Manual latency measurement"
 * buttons.
 * Manual mode counts down 5..0, plays a 0.2s 1000Hz beep at 0, and measures
 * reaction latency until Space or button press.
 * Automatic mode connects to an RTMP feed, splits the window into a red target
 * half and live feed half, counts down 3..0 once red is detected in the feed,
 * switches to green at 0, and measures latency until green is detected in the
 * feed.
 */

#ifndef LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_

#include <SDL.h>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "live_renderer/feeds/rtsp_feed_reader.hpp"

struct ImGuiContext;

namespace live_renderer {

/**
 * @brief Window for measuring end-to-end audio/visual or RTMP feed latency.
 */
class LatencyMeterWindow {
public:
    static constexpr int kCountdownSeconds = 5;
    static constexpr int kAutoCountdownSeconds = 3;
    static constexpr int kBeepFrequencyHz = 1000;
    static constexpr int kBeepDurationMs = 200;

    enum class Mode {
        kSelection,
        kManual,
        kAutomatic
    };

    enum class AutoPhase {
        kEnterAddress,
        kWaitingForRed,
        kCountdownToGreen,
        kWaitingForGreen,
        kMeasured
    };

    using BeepCallback = std::function<void(int frequency_hz, int duration_ms)>;

    struct Callbacks {
        std::function<void(int64_t latency_ms)> on_latency_changed;
    };

    explicit LatencyMeterWindow(
        BeepCallback beep_callback = nullptr,
        FeedReaderFactory feed_reader_factory = nullptr);
    ~LatencyMeterWindow();

    LatencyMeterWindow(const LatencyMeterWindow&) = delete;
    LatencyMeterWindow& operator=(const LatencyMeterWindow&) = delete;

    void SetCallbacks(Callbacks callbacks);
    void SetBeepCallback(BeepCallback callback);
    void SetFeedReaderFactory(FeedReaderFactory factory);

    void SetLatencyMs(int64_t latency_ms);
    int64_t GetLatencyMs() const { return latency_ms_; }
    bool SetLatencyFromText(const std::string& text);
    static bool TryParseLatencyMs(
        const std::string& text,
        int64_t& out_latency_ms);

    /**
     * @brief Opens the Latency Meter OS window at the mode selection screen.
     *
     * @return True if opened (or already open), false if window creation failed.
     */
    bool Open();

    /**
     * @brief Closes the Latency Meter window and releases its resources.
     */
    void Close();

    /**
     * @brief Returns true if the Latency Meter window is currently open.
     */
    bool IsOpen() const { return is_open_; }

    /**
     * @brief Processes an SDL event if it targets the Latency Meter window.
     *
     * @param event SDL event to inspect.
     * @return True if handled by the Latency Meter window.
     */
    bool HandleEvent(const SDL_Event& event);

    /**
     * @brief Updates state and renders one frame if open.
     */
    void Render();

    // Deterministic state machine API (also used by unit tests)
    void ShowModeSelection();
    void Reset(int64_t now_ms);
    void StartAutomaticSetup();
    bool StartAutomaticFeed(const std::string& address_or_url, int64_t now_ms);
    void Update(int64_t now_ms);
    bool TriggerResponse(int64_t now_ms);

    Mode GetMode() const { return mode_; }
    AutoPhase GetAutoPhase() const { return auto_phase_; }
    int GetCurrentCount() const { return current_count_; }
    int GetAutoCount() const { return auto_count_; }
    bool HasReachedZero() const { return zero_reached_; }
    bool HasMeasuredLatency() const { return measured_; }
    int64_t GetMeasuredLatencyMs() const { return measured_latency_ms_; }
    std::string GetRtmpError() const { return rtmp_error_; }

    static std::string NormalizeRtmpUrl(const std::string& input);
    static bool IsMajorityRed(
        const std::vector<uint8_t>& rgba,
        int width,
        int height);
    static bool IsMajorityGreen(
        const std::vector<uint8_t>& rgba,
        int width,
        int height);

private:
    static int64_t GetSteadyNowMs();
    static void PlayDefaultBeep(int frequency_hz, int duration_ms);

    void UpdateManual(int64_t now_ms);
    void UpdateAutomatic(int64_t now_ms);
    void UploadFeedTexture();
    void ReleaseFeedResources();

    void RenderContents(int64_t now_ms);
    void RenderSelection(int64_t now_ms);
    void RenderManual(int64_t now_ms);
    void RenderAutomatic(int64_t now_ms);
    void RenderAutomaticAddressEntry(int64_t now_ms);
    void RenderAutomaticSplitView();
    void RenderMeasuredResult();

    Callbacks callbacks_;
    BeepCallback beep_callback_;
    FeedReaderFactory feed_reader_factory_;

    int64_t latency_ms_ = 0;
    char latency_input_buf_[64]{"0"};
    bool latency_input_valid_ = true;

    bool is_open_ = false;
    SDL_Window* sdl_window_ = nullptr;
    SDL_GLContext gl_context_ = nullptr;
    ImGuiContext* imgui_context_ = nullptr;
    uint32_t sdl_window_id_ = 0;

    Mode mode_ = Mode::kManual;

    // Manual mode state
    int64_t start_time_ms_ = 0;
    int64_t zero_time_ms_ = 0;
    int current_count_ = kCountdownSeconds;
    bool zero_reached_ = false;
    bool measured_ = false;
    int64_t measured_latency_ms_ = 0;

    // Automatic (RTMP) mode state
    AutoPhase auto_phase_ = AutoPhase::kEnterAddress;
    char rtmp_address_buf_[256]{};
    std::string rtmp_error_;
    std::unique_ptr<IFeedReader> feed_reader_;
    std::vector<uint8_t> frame_rgba_;
    int frame_width_ = 0;
    int frame_height_ = 0;
    uint64_t frame_seq_ = 0;
    unsigned int feed_texture_id_ = 0;
    int texture_width_ = 0;
    int texture_height_ = 0;
    uint64_t uploaded_seq_ = 0;
    int64_t auto_countdown_start_ms_ = 0;
    int64_t green_start_ms_ = 0;
    int auto_count_ = kAutoCountdownSeconds;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_
