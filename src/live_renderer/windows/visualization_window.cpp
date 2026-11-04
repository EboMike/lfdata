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

    // If an element is highlighted (e.g. selected in UI Editor), append orange rectangle & overlay
    if (highlight_element_index >= 0 &&
        highlight_element_index < static_cast<int>(config_.elements.size())) {
        const auto& el = config_.elements[highlight_element_index];
        const auto px = RelativeToPixelRect(el.rect);

        // Subtle translucent orange fill
        RenderCommand fill_cmd;
        fill_cmd.type = RenderCommand::Type::SolidQuad;
        fill_cmd.pixel_rect = px;
        fill_cmd.color_rgba = {1.0f, 0.55f, 0.0f, 0.25f};
        batch.commands.push_back(fill_cmd);

        // 2px wide orange border outline around bounds
        constexpr float kBorder = 2.0f;

        RenderCommand top;
        top.type = RenderCommand::Type::SolidQuad;
        top.pixel_rect = {px[0] - kBorder, px[1] - kBorder, px[2] + 2.0f * kBorder, kBorder};
        top.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(top);

        RenderCommand bot;
        bot.type = RenderCommand::Type::SolidQuad;
        bot.pixel_rect = {px[0] - kBorder, px[1] + px[3], px[2] + 2.0f * kBorder, kBorder};
        bot.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(bot);

        RenderCommand left;
        left.type = RenderCommand::Type::SolidQuad;
        left.pixel_rect = {px[0] - kBorder, px[1], kBorder, px[3]};
        left.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(left);

        RenderCommand right;
        right.type = RenderCommand::Type::SolidQuad;
        right.pixel_rect = {px[0] + px[2], px[1], kBorder, px[3]};
        right.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(right);

        // Resize handle at bottom-right corner
        constexpr float kHandle = 8.0f;
        RenderCommand handle;
        handle.type = RenderCommand::Type::SolidQuad;
        handle.pixel_rect = {
            px[0] + px[2] - kHandle,
            px[1] + px[3] - kHandle,
            kHandle + kBorder,
            kHandle + kBorder
        };
        handle.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(handle);
    }

    return batch;
}

ElementConfig VisualizationWindow::ResolveElementFont(
    const ElementConfig& element) const {
    ElementConfig el = element;
    if (el.font.empty() || el.font == "default") {
        el.font = ui_config_.default_font;
    }
    return el;
}

void VisualizationWindow::GenerateElementCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const ElementConfig resolved_el = ResolveElementFont(element);
    const auto px_rect = RelativeToPixelRect(resolved_el.rect);
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        resolved_el.font_size, static_cast<float>(GetHeight()));

    if (resolved_el.type == "user_text") {
        TextComponent::GenerateUserTextCommands(
            resolved_el, state, px_rect, static_cast<float>(GetHeight()), batch);
    } else if (resolved_el.type == "game_timer") {
        GenerateGameTimerCommands(resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "user_image") {
        if (!resolved_el.image_file.empty()) {
            RenderCommand cmd;
            cmd.type = RenderCommand::Type::TexturedQuad;
            cmd.pixel_rect = px_rect;
            cmd.texture_asset = resolved_el.image_file;
            cmd.opacity = resolved_el.opacity;
            batch.commands.push_back(cmd);
        }
    } else if (resolved_el.type == "team_scorecard") {
        int team_id = resolved_el.team_index;
        if (team_id <= 0 && !state.teams.empty()) {
            team_id = state.teams.begin()->first;
        }
        GenerateTeamScorecardCommands(
            resolved_el, team_id, state, current_time_ms, batch);
    } else if (resolved_el.type == "game_scorecard") {
        GenerateGameScorecardCommands(
            resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "event_scroller") {
        GenerateEventScrollerCommands(
            resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "player_profile_picture") {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = px_rect;
        cmd.texture_asset = resolved_el.image_file.empty()
            ? "assets/sm5/commander.png" : resolved_el.image_file;
        cmd.opacity = resolved_el.opacity;
        batch.commands.push_back(cmd);
    } else if (resolved_el.type == "team_logo") {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = px_rect;
        cmd.texture_asset = resolved_el.image_file.empty()
            ? "assets/ball.png" : resolved_el.image_file;
        cmd.opacity = resolved_el.opacity;
        batch.commands.push_back(cmd);
    } else {
        // Player elements: player_name, player_role, player_score, etc.
        PlayerSnapshot sample_player{
            11, "AlphaCommander", "#101", 1, "commander",
            8200, 12, 45, 3, 20, 2, 0, false};
        std::string team_color = "#FF5000";

        for (const auto& [pid, p] : state.players) {
            if (!p.is_dummy) {
                sample_player = p;
                auto tit = state.teams.find(p.team_id);
                if (tit != state.teams.end()) {
                    team_color = tit->second.rgb;
                }
                break;
            }
        }
        TextComponent::GeneratePlayerElementCommands(
            resolved_el,
            sample_player,
            team_color,
            px_rect,
            static_cast<float>(GetHeight()),
            batch);
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
    cmd.font = (element.font.empty() || element.font == "default")
        ? ui_config_.default_font
        : element.font;
    cmd.hex_color = element.color.empty() ? "#ffffff" : element.color;
    cmd.font_size_px = font_size_px;
    cmd.alignment = element.alignment.empty() ? "center" : element.alignment;
    cmd.black_outline = true;
    batch.commands.push_back(cmd);
}

float VisualizationWindow::ComputeTeamScorecardHeightPx(
    const ElementConfig& element,
    int team_id,
    const GameStateSnapshot& state) const {
    const float row_height_px = 32.0f;
    float height = 0.0f;

    const TemplateConfig* header_tmpl =
        FindTemplate(element.header_template_id);
    if (header_tmpl != nullptr && !header_tmpl->elements.empty()) {
        height += row_height_px + 4.0f + element.vertical_spacing;
    }

    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, element.add_totals);

    if (!player_ids.empty()) {
        const float row_spacing = 2.0f + element.vertical_spacing;
        height += static_cast<float>(player_ids.size()) *
            (row_height_px + row_spacing);
    }

    return height;
}

void VisualizationWindow::GenerateTeamScorecardCommands(
    const ElementConfig& element,
    int team_id,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const auto it = state.teams.find(team_id);
    if (it == state.teams.end()) return;
    const auto& team = it->second;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float row_height_px = 32.0f;
    float current_y = base_px_rect[1];

    // Optional header template
    const TemplateConfig* header_tmpl =
        FindTemplate(element.header_template_id);
    if (header_tmpl != nullptr && !header_tmpl->elements.empty()) {
        for (const auto& hel : header_tmpl->elements) {
            std::array<float, 4> hp_rect{
                base_px_rect[0] + (hel.rect[0] * base_px_rect[2]),
                current_y + (hel.rect[1] * row_height_px),
                hel.rect[2] * base_px_rect[2],
                hel.rect[3] * row_height_px
            };
            TextComponent::GenerateCommands(
                ResolveElementFont(hel),
                hel.text.empty() ? "PLAYER" : hel.text,
                hp_rect,
                team.rgb,
                false,
                static_cast<float>(GetHeight()),
                batch);
        }
        current_y += row_height_px + 4.0f + element.vertical_spacing;
    }

    const float start_players_y = current_y;

    // Sorted player rows
    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, element.add_totals);

    const TemplateConfig* row_tmpl = FindTemplate(element.row_template_id);

    const std::string list_key =
        std::to_string(config_.id) + "_team_" + std::to_string(team_id);

    const float row_spacing = 2.0f + element.vertical_spacing;
    for (size_t row_idx = 0; row_idx < player_ids.size(); ++row_idx) {
        int pid = player_ids[row_idx];
        auto pit = state.players.find(pid);
        if (pit == state.players.end()) continue;
        const auto& player = pit->second;

        const float target_row_y = start_players_y +
            static_cast<float>(row_idx) * (row_height_px + row_spacing);

        const float row_y = list_animation_tracker_.GetAnimatedPosition(
            list_key,
            pid,
            target_row_y,
            current_time_ms,
            element.change_animation,
            element.animation_duration);

        if (row_tmpl != nullptr && !row_tmpl->elements.empty()) {
            for (const auto& rel : row_tmpl->elements) {
                std::array<float, 4> rpx_rect{
                    base_px_rect[0] + (rel.rect[0] * base_px_rect[2]),
                    row_y + (rel.rect[1] * row_height_px),
                    rel.rect[2] * base_px_rect[2],
                    rel.rect[3] * row_height_px
                };
                TextComponent::GeneratePlayerElementCommands(
                    ResolveElementFont(rel),
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
            d_name_el.font =
                (element.font.empty() || element.font == "default")
                    ? ui_config_.default_font
                    : element.font;
            d_name_el.font_size = 18.0f;
            d_name_el.alignment = "left";
            TextComponent::GeneratePlayerElementCommands(
                d_name_el, player, team.rgb,
                {base_px_rect[0], row_y, base_px_rect[2] * 0.60f,
                 row_height_px},
                static_cast<float>(GetHeight()), batch);

            ElementConfig d_score_el;
            d_score_el.type = "player_score";
            d_score_el.font =
                (element.font.empty() || element.font == "default")
                    ? ui_config_.default_font
                    : element.font;
            d_score_el.font_size = 18.0f;
            d_score_el.alignment = "right";
            TextComponent::GeneratePlayerElementCommands(
                d_score_el, player, team.rgb,
                {base_px_rect[0] + base_px_rect[2] * 0.65f, row_y,
                 base_px_rect[2] * 0.35f, row_height_px},
                static_cast<float>(GetHeight()), batch);
        }
    }
}

void VisualizationWindow::GenerateGameScorecardCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const TeamSortOrder t_sort = (element.sort_order == "index")
        ? TeamSortOrder::Index
        : TeamSortOrder::Ranking;
    const auto team_ids = ScorecardHelper::GetSortedTeamIds(state, t_sort);
    if (team_ids.empty()) return;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float win_h = static_cast<float>(GetHeight());
    const std::string team_list_key =
        std::to_string(config_.id) + "_game_teams";

    if (element.orientation == "horizontal") {
        const float section_width_rel =
            1.0f / static_cast<float>(team_ids.size());

        for (size_t i = 0; i < team_ids.size(); ++i) {
            ElementConfig sub_el = element;
            sub_el.team_index = team_ids[i];
            const float target_rel_x =
                element.rect[0] +
                (static_cast<float>(i) * section_width_rel * element.rect[2]);
            const float anim_rel_x =
                list_animation_tracker_.GetAnimatedPosition(
                    team_list_key,
                    team_ids[i],
                    target_rel_x,
                    current_time_ms,
                    element.change_animation,
                    element.animation_duration);
            sub_el.rect[0] = anim_rel_x;
            sub_el.rect[2] = section_width_rel * element.rect[2];

            GenerateTeamScorecardCommands(
                sub_el, team_ids[i], state, current_time_ms, batch);
        }
    } else {
        // Vertical orientation: render team scorecards one below the other
        float curr_px_y = base_px_rect[1];

        for (size_t i = 0; i < team_ids.size(); ++i) {
            ElementConfig sub_el = element;
            sub_el.team_index = team_ids[i];

            const float target_rel_y = curr_px_y / win_h;
            const float anim_rel_y =
                list_animation_tracker_.GetAnimatedPosition(
                    team_list_key,
                    team_ids[i],
                    target_rel_y,
                    current_time_ms,
                    element.change_animation,
                    element.animation_duration);

            float team_h_px = ComputeTeamScorecardHeightPx(
                sub_el, team_ids[i], state);
            if (team_h_px <= 0.0f) {
                team_h_px = base_px_rect[3] /
                    static_cast<float>(team_ids.size());
            }

            sub_el.rect[1] = anim_rel_y;
            sub_el.rect[3] = team_h_px / win_h;

            GenerateTeamScorecardCommands(
                sub_el, team_ids[i], state, current_time_ms, batch);

            const float team_spacing_px = 16.0f + element.vertical_spacing;
            curr_px_y += team_h_px + team_spacing_px;
        }
    }
}

void VisualizationWindow::GenerateEventScrollerCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    if (state.event_scroller.empty()) return;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const float win_h = static_cast<float>(GetHeight());
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        element.font_size > 0.0f ? element.font_size : 16.0f, win_h);
    const float line_h = font_size_px * 1.4f;
    const float line_spacing = font_size_px * 0.15f + element.vertical_spacing;
    const float step_y = line_h + line_spacing;

    const size_t num_events = state.event_scroller.size();
    const int idx = static_cast<int>(num_events) - 1;
    const float target_offset = static_cast<float>(idx) * step_y;

    float y_scroll = target_offset;
    if (state.in_session && state.game_start_time_local_ms > 0) {
        const int64_t t_latest = state.event_scroller.back().timestamp_ms;
        const int64_t current_game_time_ms =
            current_time_ms - state.game_start_time_local_ms;
        const int64_t elapsed_ms = current_game_time_ms - t_latest;
        constexpr int64_t kScrollDurationMs = 500;
        if (elapsed_ms >= 0 && elapsed_ms < kScrollDurationMs) {
            float p = static_cast<float>(elapsed_ms) /
                static_cast<float>(kScrollDurationMs);
            constexpr float kPi = 3.14159265358979323846f;
            float p_anim = 0.5f * (1.0f - std::cos(p * kPi));
            float prev_offset =
                static_cast<float>(std::max(0, idx - 1)) * step_y;
            y_scroll = prev_offset + (target_offset - prev_offset) * p_anim;
        }
    }

    ElementConfig line_el = element;
    line_el.font = (element.font.empty() || element.font == "default")
        ? ui_config_.default_font
        : element.font;
    line_el.font_size = element.font_size > 0.0f ? element.font_size : 16.0f;
    line_el.alignment = element.alignment.empty() ? "left" : element.alignment;
    line_el.color = element.color.empty() ? "#ffffff" : element.color;

    const float container_bottom = base_px_rect[1] + base_px_rect[3];
    for (size_t i = 0; i < num_events; ++i) {
        float y = (container_bottom - line_h) +
            (static_cast<float>(i) * step_y - y_scroll);

        if (y + line_h < base_px_rect[1] || y > container_bottom) {
            continue;
        }

        const auto& ev = state.event_scroller[i];
        TextComponent::GenerateCommands(
            line_el,
            ev.formatted_message,
            {base_px_rect[0], y, base_px_rect[2], line_h},
            line_el.color,
            false,
            win_h,
            batch,
            element.tilt,
            base_px_rect,
            true);
    }
}

}  // namespace live_renderer

