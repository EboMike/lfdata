#include "live_renderer/windows/visualization_window.hpp"
#include <algorithm>
#include "live_renderer/components/game_timer_element.hpp"
#include "live_renderer/components/scorecard_helper.hpp"
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

RenderBatch VisualizationWindow::GenerateBatch(const GameStateSnapshot& state, int64_t current_time_ms) const {
    RenderBatch batch;
    batch.window_width = GetWidth();
    batch.window_height = GetHeight();

    for (const auto& el : config_.elements) {
        GenerateElementCommands(el, state, current_time_ms, batch);
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
        std::string text = RichTextLayout::SubstitutePlaceholders(element.text, state);
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::Text;
        cmd.pixel_rect = px_rect;
        cmd.text = text;
        cmd.hex_color = element.color.empty() ? "#ffffff" : element.color;
        cmd.font_size_px = font_size_px;
        cmd.alignment = element.alignment;
        cmd.black_outline = true;
        batch.commands.push_back(cmd);
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
            RenderCommand hcmd;
            hcmd.type = RenderCommand::Type::Text;
            hcmd.pixel_rect = hp_rect;
            hcmd.text = hel.text.empty() ? "PLAYER" : hel.text;
            hcmd.hex_color = team.rgb;
            hcmd.font_size_px = RichTextLayout::ComputePixelFontSize(
                hel.font_size > 0.0f ? hel.font_size : 18.0f, static_cast<float>(GetHeight()));
            hcmd.alignment = hel.alignment;
            hcmd.black_outline = true;
            batch.commands.push_back(hcmd);
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
        const std::string row_color = ScorecardHelper::GetRowTextColor(player, team.rgb);

        if (row_tmpl != nullptr && !row_tmpl->elements.empty()) {
            for (const auto& rel : row_tmpl->elements) {
                std::array<float, 4> rpx_rect{
                    base_px_rect[0] + (rel.rect[0] * base_px_rect[2]),
                    current_y + (rel.rect[1] * row_height_px),
                    rel.rect[2] * base_px_rect[2],
                    rel.rect[3] * row_height_px
                };

                RenderCommand rcmd;
                rcmd.type = RenderCommand::Type::Text;
                rcmd.pixel_rect = rpx_rect;
                rcmd.hex_color = row_color;
                rcmd.font_size_px = RichTextLayout::ComputePixelFontSize(
                    rel.font_size > 0.0f ? rel.font_size : 18.0f, static_cast<float>(GetHeight()));
                rcmd.alignment = rel.alignment;
                rcmd.black_outline = true;

                if (rel.type == "player_name") {
                    rcmd.text = player.is_dummy ? "TOTALS" : player.name;
                } else if (rel.type == "player_score") {
                    rcmd.text = std::to_string(player.score);
                } else if (rel.type == "player_lives") {
                    rcmd.text = std::to_string(player.lives);
                } else if (rel.type == "player_ammo") {
                    rcmd.text = std::to_string(player.shots);
                } else if (rel.type == "player_missiles") {
                    rcmd.text = std::to_string(player.missiles);
                } else if (rel.type == "player_special_points") {
                    rcmd.text = std::to_string(player.special_points);
                } else if (rel.type == "player_role") {
                    if (!player.role.empty()) {
                        rcmd.type = RenderCommand::Type::TexturedQuad;
                        rcmd.texture_asset = "assets/sm5/" + player.role + ".png";
                    } else {
                        continue;
                    }
                } else {
                    rcmd.text = rel.text;
                }
                batch.commands.push_back(rcmd);
            }
        } else {
            // Default row formatting if no template specified
            RenderCommand dcmd;
            dcmd.type = RenderCommand::Type::Text;
            dcmd.pixel_rect = {base_px_rect[0], current_y, base_px_rect[2] * 0.60f, row_height_px};
            dcmd.text = player.is_dummy ? "TOTALS" : player.name;
            dcmd.hex_color = row_color;
            dcmd.font_size_px = 18.0f;
            batch.commands.push_back(dcmd);

            RenderCommand scmd;
            scmd.type = RenderCommand::Type::Text;
            scmd.pixel_rect = {base_px_rect[0] + base_px_rect[2] * 0.65f, current_y, base_px_rect[2] * 0.35f, row_height_px};
            scmd.text = std::to_string(player.score);
            scmd.hex_color = row_color;
            scmd.font_size_px = 18.0f;
            scmd.alignment = "right";
            batch.commands.push_back(scmd);
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

        RenderCommand cmd;
        cmd.type = RenderCommand::Type::Text;
        cmd.pixel_rect = {base_px_rect[0], y, base_px_rect[2], line_h};
        cmd.text = it->formatted_message;
        cmd.hex_color = element.color.empty() ? "#ffffff" : element.color;
        cmd.font_size_px = 16.0f;
        cmd.alignment = "left";
        cmd.black_outline = true;
        batch.commands.push_back(cmd);

        y -= (line_h + 2.0f);
    }
}

}  // namespace live_renderer

