/**
 * @file latency_meter_window.hpp
 * @brief Separate window implementing the audio/visual latency meter.
 *
 * Counts down from 5 to 0 in seconds with a large centered digit, plays a
 * 0.2-second 1000Hz beep upon reaching 0, and measures the elapsed milliseconds
 * between reaching 0 and the user pressing Space or clicking the button.
 */

#ifndef LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_

#include <SDL.h>
#include <cstdint>
#include <functional>

struct ImGuiContext;

namespace live_renderer {

/**
 * @brief Window for measuring end-to-end audio/visual reaction latency.
 */
class LatencyMeterWindow {
public:
    static constexpr int kCountdownSeconds = 5;
    static constexpr int kBeepFrequencyHz = 1000;
    static constexpr int kBeepDurationMs = 200;

    using BeepCallback = std::function<void(int frequency_hz, int duration_ms)>;

    explicit LatencyMeterWindow(BeepCallback beep_callback = nullptr);
    ~LatencyMeterWindow();

    LatencyMeterWindow(const LatencyMeterWindow&) = delete;
    LatencyMeterWindow& operator=(const LatencyMeterWindow&) = delete;

    void SetBeepCallback(BeepCallback callback);

    /**
     * @brief Opens the Latency Meter OS window and starts the 5..0 countdown.
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
     * @brief Updates the countdown state and renders one frame if open.
     */
    void Render();

    // Deterministic state machine API (also used by unit tests)
    void Reset(int64_t now_ms);
    void Update(int64_t now_ms);
    bool TriggerResponse(int64_t now_ms);

    int GetCurrentCount() const { return current_count_; }
    bool HasReachedZero() const { return zero_reached_; }
    bool HasMeasuredLatency() const { return measured_; }
    int64_t GetMeasuredLatencyMs() const { return measured_latency_ms_; }

private:
    static int64_t GetSteadyNowMs();
    static void PlayDefaultBeep(int frequency_hz, int duration_ms);

    void RenderContents(int64_t now_ms);

    BeepCallback beep_callback_;

    bool is_open_ = false;
    SDL_Window* sdl_window_ = nullptr;
    SDL_GLContext gl_context_ = nullptr;
    ImGuiContext* imgui_context_ = nullptr;
    uint32_t sdl_window_id_ = 0;

    int64_t start_time_ms_ = 0;
    int64_t zero_time_ms_ = 0;
    int current_count_ = kCountdownSeconds;
    bool zero_reached_ = false;
    bool measured_ = false;
    int64_t measured_latency_ms_ = 0;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_LATENCY_METER_WINDOW_HPP_
