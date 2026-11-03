#include "live_renderer/windows/visualization_window.hpp"
#include <algorithm>
#include "live_renderer/components/game_timer_element.hpp"
#include "live_renderer/components/scorecard_helper.hpp"
#include "live_renderer/components/text_component.hpp"
#include "live_renderer/render/rich_text_layout.hpp"

namespace live_renderer {

VisualizationWindow::VisualizationWindow(WindowConfig config, const UIConfig& ui_config)
    : config_(std::move(config)),
      ui_config_(ui_config) {}

void VisualizationWindow::SetDimensions(int width, int height) {
    config_.rect[2] = std::max(100, width);
    config_.rect[3] = std::max(100, height);
}

std::array<float, 4> VisualizationWindow::RelativeToPixelRect(const std::array<float, 4>& rel_rect) const {
    const float win_w = static_cast<float>(GetWidth());
    const float win_h = static_cast<float>(GetHeight());
    return {
        rel_rect[0] * win_w,
        rel_rect[1] * win_h,
        rel_rect[2] * win_w,
        rel_rect[3] * win_h
    };
}

const TemplateConfig* VisualizationWindow::FindTemplate(int template_id) const {
    if (template_id <= 0) return nullptr;
    for (const auto& tmpl : ui_config_.templates) {
        if (tmpl.id == template_id) {
            return &tmpl;
        }
    }
    return nullptr;
}

RenderBatch VisualizationWindow::GenerateBatch(
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    int highlight_element_index) const {
    RenderBatch batch;
    batch.window_width = GetWidth();
    batch.window_height = GetHeight();

    // Render elements in order of z_position (lower Z drawn first, higher Z on top)
    std::vector<const ElementConfig*> ordered_elements;
    ordered_elements.reserve(config_.elements.size());
    for (const auto& el : config_.elements) {
        ordered_elements.push_back(&el);
    }
    std::stable_sort(
        ordered_elements.begin(),
        ordered_elements.end(),
        [](const ElementConfig* a, const ElementConfig* b) {
            return a->z_position < b->z_position;
        });

    for (const auto* el : ordered_elements) {
        GenerateElementCommands(*el, state, current_time_ms, batch);
    }

    // If an element is highlighted (e.g. selected in UI Editor), append border & translucent overlay
    if (highlight_element_index >= 0 &&
        highlight_element_index < static_cast<int>(config_.elements.size())) {
        const auto& el = config_.elements[highlight_element_index];
        const auto px = RelativeToPixelRect(el.rect);

        // Subtle translucent fill
        RenderCommand fill_cmd;
        fill_cmd.type = RenderCommand::Type::SolidQuad;
        fill_cmd.pixel_rect = px;
        fill_cmd.color_rgba = {1.0f, 0.85f, 0.2f, 0.25f};
        batch.commands.push_back(fill_cmd);

        // 2px wide golden border outline around bounds
        constexpr float kBorder = 2.0f;

        RenderCommand top;
        top.type = RenderCommand::Type::SolidQuad;
        top.pixel_rect = {px[0] - kBorder, px[1] - kBorder, px[2] + 2.0f * kBorder, kBorder};
        top.color_rgba = {1.0f, 0.9f, 0.15f, 0.95f};
        batch.commands.push_back(top);

        RenderCommand bot;
        bot.type = RenderCommand::Type::SolidQuad;
        bot.pixel_rect = {px[0] - kBorder, px[1] + px[3], px[2] + 2.0f * kBorder, kBorder};
        bot.color_rgba = {1.0f, 0.9f, 0.15f, 0.95f};
        batch.commands.push_back(bot);

        RenderCommand left;
        left.type = RenderCommand::Type::SolidQuad;
        left.pixel_rect = {px[0] - kBorder, px[1], kBorder, px[3]};
        left.color_rgba = {1.0f, 0.9f, 0.15f, 0.95f};
        batch.commands.push_back(left);

        RenderCommand right;
        right.type = RenderCommand::Type::SolidQuad;
        right.pixel_rect = {px[0] + px[2], px[1], kBorder, px[3]};
        right.color_rgba = {1.0f, 0.9f, 0.15f, 0.95f};
        batch.commands.push_back(right);
    }

    return batch;
}

void VisualizationWindow::GenerateElementCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const auto px_rect = RelativeToPixelRect(element.rect);
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        element.font_size, static_cast<float>(GetHeight()));

    if (element.type == "user_text") {
        TextComponent::GenerateUserTextCommands(
            element, state, px_rect, static_cast<float>(GetHeight()), batch);
    } else if (element.type == "game_timer") {
        GenerateGameTimerCommands(element, state, current_time_ms, batch);
    } else if (element.type == "user_image") {
        if (!element.image_file.empty()) {
            RenderCommand cmd;
            cmd.type = RenderCommand::Type::TexturedQuad;
            cmd.pixel_rect = px_rect;
            cmd.texture_asset = element.image_file;
            cmd.opacity = element.opacity;
            batch.commands.push_back(cmd);
        }
    } else if (element.type == "team_scorecard") {
        int team_id = element.team_index;
        if (team_id <= 0 && !state.teams.empty()) {
            team_id = state.teams.begin()->first;
        }
        GenerateTeamScorecardCommands(element, team_id, state, batch);
    } else if (element.type == "game_scorecard") {
        GenerateGameScorecardCommands(element, state, batch);
    } else if (element.type == "event_scroller") {
        GenerateEventScrollerCommands(element, state, batch);
    }
}

void VisualizationWindow::GenerateGameTimerCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const auto px_rect = RelativeToPixelRect(element.rect);
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        element.font_size, static_cast<float>(GetHeight()));

    RenderCommand cmd;
    cmd.type = RenderCommand::Type::Text;
    cmd.pixel_rect = px_rect;
    cmd.text = GameTimerElement::FormatRemainingTime(state, current_time_ms);
    cmd.hex_color = element.color.empty() ? "#ffffff" : element.color;
    cmd.font_size_px = font_size_px;
    cmd.alignment = element.alignment.empty() ? "center" : element.alignment;
    cmd.black_outline = true;
    batch.commands.push_back(cmd);
}

void VisualizationWindow::GenerateTeamScorecardCommands(
    const ElementConfig& element,
    int team_id,
    const GameStateSnapshot& state,
    RenderBatch& batch) const {
    const auto it = state.teams.find(team_id);
    if (it == state.teams.end()) return;
    const auto& team = it->second;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float row_height_px = 32.0f;
    float current_y = base_px_rect[1];

    // Optional header template
    const TemplateConfig* header_tmpl = FindTemplate(element.header_template_id);
    if (header_tmpl != nullptr && !header_tmpl->elements.empty()) {
        for (const auto& hel : header_tmpl->elements) {
            std::array<float, 4> hp_rect{
                base_px_rect[0] + (hel.rect[0] * base_px_rect[2]),
                current_y + (hel.rect[1] * row_height_px),
                hel.rect[2] * base_px_rect[2],
                hel.rect[3] * row_height_px
            };
            TextComponent::GenerateCommands(
                hel,
                hel.text.empty() ? "PLAYER" : hel.text,
                hp_rect,
                team.rgb,
                false,
                static_cast<float>(GetHeight()),
                batch);
        }
        current_y += row_height_px + 4.0f;
    }

    // Sorted player rows
    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, element.add_totals);

    const TemplateConfig* row_tmpl = FindTemplate(element.row_template_id);

    for (int pid : player_ids) {
        auto pit = state.players.find(pid);
        if (pit == state.players.end()) continue;
        const auto& player = pit->second;

        if (row_tmpl != nullptr && !row_tmpl->elements.empty()) {
            for (const auto& rel : row_tmpl->elements) {
                std::array<float, 4> rpx_rect{
                    base_px_rect[0] + (rel.rect[0] * base_px_rect[2]),
                    current_y + (rel.rect[1] * row_height_px),
                    rel.rect[2] * base_px_rect[2],
                    rel.rect[3] * row_height_px
                };
                TextComponent::GeneratePlayerElementCommands(
                    rel,
                    player,
                    team.rgb,
                    rpx_rect,
                    static_cast<float>(GetHeight()),
                    batch);
            }
        } else {
            // Default row formatting if no template specified
            ElementConfig d_name_el;
            d_name_el.type = "player_name";
            d_name_el.font_size = 18.0f;
            d_name_el.alignment = "left";
            TextComponent::GeneratePlayerElementCommands(
                d_name_el, player, team.rgb,
                {base_px_rect[0], current_y, base_px_rect[2] * 0.60f, row_height_px},
                static_cast<float>(GetHeight()), batch);

            ElementConfig d_score_el;
            d_score_el.type = "player_score";
            d_score_el.font_size = 18.0f;
            d_score_el.alignment = "right";
            TextComponent::GeneratePlayerElementCommands(
                d_score_el, player, team.rgb,
                {base_px_rect[0] + base_px_rect[2] * 0.65f, current_y, base_px_rect[2] * 0.35f, row_height_px},
                static_cast<float>(GetHeight()), batch);
        }
        current_y += row_height_px + 2.0f;
    }
}

void VisualizationWindow::GenerateGameScorecardCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    RenderBatch& batch) const {
    const TeamSortOrder t_sort = (element.sort_order == "index")
        ? TeamSortOrder::Index
        : TeamSortOrder::Ranking;
    const auto team_ids = ScorecardHelper::GetSortedTeamIds(state, t_sort);
    if (team_ids.empty()) return;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float section_width_rel = 1.0f / static_cast<float>(team_ids.size());

    for (size_t i = 0; i < team_ids.size(); ++i) {
        ElementConfig sub_el = element;
        sub_el.team_index = team_ids[i];
        if (element.orientation == "horizontal") {
            sub_el.rect[0] = element.rect[0] + (static_cast<float>(i) * section_width_rel * element.rect[2]);
            sub_el.rect[2] = section_width_rel * element.rect[2];
        }
        GenerateTeamScorecardCommands(sub_el, team_ids[i], state, batch);
    }
}

void VisualizationWindow::GenerateEventScrollerCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    RenderBatch& batch) const {
    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float line_h = 24.0f;
    float y = base_px_rect[1] + base_px_rect[3] - line_h;

    // Show recent events from bottom up
    for (auto it = state.event_scroller.rbegin(); it != state.event_scroller.rend(); ++it) {
        if (y < base_px_rect[1]) break;

        ElementConfig line_el = element;
        line_el.font_size = element.font_size > 0.0f ? element.font_size : 16.0f;
        line_el.alignment = "left";

        TextComponent::GenerateCommands(
            line_el,
            it->formatted_message,
            {base_px_rect[0], y, base_px_rect[2], line_h},
            element.color.empty() ? "#ffffff" : element.color,
            false,
            static_cast<float>(GetHeight()),
            batch);

        y -= (line_h + 2.0f);
    }
}

}  // namespace live_renderer

