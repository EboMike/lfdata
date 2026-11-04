#ifndef LIVE_RENDERER_WINDOWS_VISUALIZATION_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_VISUALIZATION_WINDOW_HPP_

#include <string>
#include <vector>
#include "live_renderer/components/event_scroller_tracker.hpp"
#include "live_renderer/components/list_animation_tracker.hpp"
#include "live_renderer/components/messages_display_tracker.hpp"
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/render/render_batch.hpp"
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Manages visualization and element layout computation for a single render window.
 *
 * Transforms relative coordinates (0.0 to 1.0) into pixel coordinates, resolves
 * placeholders, evaluates game state (scores, timers, rosters, events), and
 * generates an optimized RenderBatch for OpenGL rendering.
 */
class VisualizationWindow {
public:
    VisualizationWindow(WindowConfig config, const UIConfig& ui_config);
    ~VisualizationWindow() = default;

    const WindowConfig& GetConfig() const { return config_; }
    void SetConfig(const WindowConfig& config) { config_ = config; }

    int GetId() const { return config_.id; }
    const std::string& GetTitle() const { return config_.title; }
    int GetWidth() const { return config_.rect[2]; }
    int GetHeight() const { return config_.rect[3]; }

    void SetDimensions(int width, int height);

    /**
     * @brief Generates all 2D draw commands for the window given the active game state snapshot.
     * @param state Active GameStateSnapshot (or mock state if previewing in editor).
     * @return Prepared RenderBatch containing ordered draw commands.
     */
    RenderBatch GenerateBatch(
        const GameStateSnapshot& state,
        int64_t current_time_ms = 0,
        int highlight_element_index = -1) const;

    /**
     * @brief Converts relative rect [x, y, w, h] to absolute window pixels.
     *
     * Coordinates assume a 16:9 aspect ratio anchored at top-left (0,0),
     * where y=1.0 represents the window height and x=1.0 represents
     * height * 16 / 9.
     */
    std::array<float, 4> RelativeToPixelRect(
        const std::array<float, 4>& rel_rect) const;

private:
    void GenerateElementCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateGameTimerCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateTeamScorecardCommands(
        const ElementConfig& element,
        int team_id,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateGameScorecardCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateEventScrollerCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateImportantMessagesCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        int64_t current_time_ms,
        RenderBatch& batch) const;

    void GenerateBackgroundCommands(
        const BackgroundConfig& bg,
        const std::array<float, 4>& pixel_rect,
        int team_id,
        const GameStateSnapshot& state,
        RenderBatch& batch) const;

    const TemplateConfig* FindTemplate(int template_id) const;
    ElementConfig ResolveElementFont(const ElementConfig& element) const;
    float ComputeTeamScorecardHeightPx(
        const ElementConfig& element,
        int team_id,
        const GameStateSnapshot& state) const;

    WindowConfig config_;
    const UIConfig& ui_config_;
    mutable ListAnimationTracker list_animation_tracker_;
    mutable MessagesDisplayTracker messages_display_tracker_;
    mutable EventScrollerTracker event_scroller_tracker_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_VISUALIZATION_WINDOW_HPP_

