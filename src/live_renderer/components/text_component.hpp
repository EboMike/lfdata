#ifndef LIVE_RENDERER_COMPONENTS_TEXT_COMPONENT_HPP_
#define LIVE_RENDERER_COMPONENTS_TEXT_COMPONENT_HPP_

#include <array>
#include <string>
#include <string_view>
#include <vector>
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/render/render_batch.hpp"
#include "live_renderer/render/rich_text_layout.hpp"
#include "live_renderer/state/game_state_snapshot.hpp"

namespace live_renderer {

/**
 * @brief Component responsible for formatting, placeholder expansion, markup parsing,
 *        and render command generation for all text elements.
 */
class TextComponent {
public:
    TextComponent() = default;
    ~TextComponent() = default;

    /**
     * @brief Resolves raw string value for a player template element.
     *
     * Formats player names, scores, lives, shots/ammo, missiles, special points,
     * goals, assists, clears, steals, and zaps.
     *
     * @param element_type Type string (e.g. "player_name", "player_score").
     * @param player PlayerSnapshot data for the player or dummy totals row.
     * @param default_text Custom text pattern or fallback.
     * @return Formatted string representation.
     */
    static std::string ResolvePlayerText(
        std::string_view element_type,
        const PlayerSnapshot& player,
        std::string_view default_text = "");

    /**
     * @brief Generates render commands for a text string within target pixel coordinates.
     *
     * Handles rich text markup (<font color="...">, [img:...]), multi-run alignment,
     * default black outline, and rapid-fire visual effects.
     *
     * @param element ElementConfig containing typography, alignment, and styling.
     * @param raw_text Pre-substituted string or markup text.
     * @param pixel_rect Absolute screen bounds [x, y, width, height] in pixels.
     * @param base_color Base fallback text color (#RRGGBB).
     * @param rapid_fire True if player has rapid fire active.
     * @param window_height Total height of window in pixels (for font scaling).
     * @param batch Destination RenderBatch to append generated commands to.
     */
    static void GenerateCommands(
        const ElementConfig& element,
        std::string_view raw_text,
        const std::array<float, 4>& pixel_rect,
        const std::string& base_color,
        bool rapid_fire,
        float window_height,
        RenderBatch& batch);

    /**
     * @brief Generates render commands for a top-level user_text element.
     *
     * Substitutes {game_type} and {center} placeholders, parses markup, and
     * generates styled text commands.
     *
     * @param element ElementConfig.
     * @param state Active GameStateSnapshot.
     * @param pixel_rect Absolute screen bounds.
     * @param window_height Total height of window in pixels.
     * @param batch Destination RenderBatch.
     */
    static void GenerateUserTextCommands(
        const ElementConfig& element,
        const GameStateSnapshot& state,
        const std::array<float, 4>& pixel_rect,
        float window_height,
        RenderBatch& batch);

    /**
     * @brief Generates render commands for a player template element within a scorecard or roster.
     *
     * Resolves player statistics, state colors (dead, down, active), rapid fire status,
     * and appends styled draw commands.
     *
     * @param element ElementConfig.
     * @param player PlayerSnapshot.
     * @param team_color Base color of player's team (#RRGGBB).
     * @param pixel_rect Absolute screen bounds.
     * @param window_height Total height of window in pixels.
     * @param batch Destination RenderBatch.
     */
    static void GeneratePlayerElementCommands(
        const ElementConfig& element,
        const PlayerSnapshot& player,
        const std::string& team_color,
        const std::array<float, 4>& pixel_rect,
        float window_height,
        RenderBatch& batch);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_COMPONENTS_TEXT_COMPONENT_HPP_

