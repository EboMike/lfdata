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

std::array<float, 4> VisualizationWindow::RelativeToPixelRect(
    const std::array<float, 4>& rel_rect) const {
    const float win_h = static_cast<float>(GetHeight());
    const float unit_w = win_h * 16.0f / 9.0f;
    if (template_extents_[0] > 0.0f && template_extents_[1] > 0.0f) {
        const float ext_w = template_extents_[0] * unit_w;
        const float ext_h = template_extents_[1] * win_h;
        return {
            rel_rect[0] * ext_w,
            rel_rect[1] * ext_h,
            rel_rect[2] * ext_w,
            rel_rect[3] * ext_h
        };
    }
    return {
        rel_rect[0] * unit_w,
        rel_rect[1] * win_h,
        rel_rect[2] * unit_w,
        rel_rect[3] * win_h
    };
}

std::array<float, 4> VisualizationWindow::ComputePaddingRect(
    const std::array<float, 4>& content_px,
    const InsetsConfig& padding,
    float ref_w,
    float ref_h) {
    const float pad_l = padding.left * ref_w;
    const float pad_r = padding.right * ref_w;
    const float pad_u = padding.up * ref_h;
    const float pad_d = padding.down * ref_h;
    return {
        content_px[0] - pad_l,
        content_px[1] - pad_u,
        content_px[2] + pad_l + pad_r,
        content_px[3] + pad_u + pad_d
    };
}

std::array<float, 4> VisualizationWindow::ComputeExtentsRect(
    const std::array<float, 4>& content_px,
    const InsetsConfig& padding,
    const InsetsConfig& margin,
    float ref_w,
    float ref_h) {
    const float pad_l = padding.left * ref_w;
    const float pad_r = padding.right * ref_w;
    const float pad_u = padding.up * ref_h;
    const float pad_d = padding.down * ref_h;

    const float mar_l = margin.left * ref_w;
    const float mar_r = margin.right * ref_w;
    const float mar_u = margin.up * ref_h;
    const float mar_d = margin.down * ref_h;

    return {
        content_px[0] - pad_l - mar_l,
        content_px[1] - pad_u - mar_u,
        content_px[2] + pad_l + pad_r + mar_l + mar_r,
        content_px[3] + pad_u + pad_d + mar_u + mar_d
    };
}

std::array<float, 4> VisualizationWindow::ComputePaddingPixelRect(
    const ElementConfig& element,
    const std::array<float, 4>& content_px_rect) const {
    const float win_h = static_cast<float>(GetHeight());
    const float unit_w = win_h * 16.0f / 9.0f;
    const float ref_w = (template_extents_[0] > 0.0f &&
                         template_extents_[1] > 0.0f)
        ? (template_extents_[0] * unit_w)
        : unit_w;
    const float ref_h = (template_extents_[0] > 0.0f &&
                         template_extents_[1] > 0.0f)
        ? (template_extents_[1] * win_h)
        : win_h;
    return ComputePaddingRect(
        content_px_rect, element.padding, ref_w, ref_h);
}

std::array<float, 4> VisualizationWindow::ComputeExtentsPixelRect(
    const ElementConfig& element,
    const std::array<float, 4>& content_px_rect) const {
    const float win_h = static_cast<float>(GetHeight());
    const float unit_w = win_h * 16.0f / 9.0f;
    const float ref_w = (template_extents_[0] > 0.0f &&
                         template_extents_[1] > 0.0f)
        ? (template_extents_[0] * unit_w)
        : unit_w;
    const float ref_h = (template_extents_[0] > 0.0f &&
                         template_extents_[1] > 0.0f)
        ? (template_extents_[1] * win_h)
        : win_h;
    return ComputeExtentsRect(
        content_px_rect, element.padding, element.margin, ref_w, ref_h);
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

    // If an element is highlighted (e.g. selected in UI Editor), append
    // orange rectangle outline around bounds (unfilled).
    if (highlight_element_index >= 0 &&
        highlight_element_index < static_cast<int>(config_.elements.size())) {
        const auto& el = config_.elements[highlight_element_index];
        const auto content_px = RelativeToPixelRect(el.rect);
        const auto px = ComputeExtentsPixelRect(el, content_px);

        // 2px wide orange border outline around bounds
        constexpr float kBorder = 2.0f;

        RenderCommand top;
        top.type = RenderCommand::Type::SolidQuad;
        top.pixel_rect = {
            px[0] - kBorder,
            px[1] - kBorder,
            px[2] + 2.0f * kBorder,
            kBorder
        };
        top.color_rgba = {1.0f, 0.55f, 0.0f, 1.0f};
        batch.commands.push_back(top);

        RenderCommand bot;
        bot.type = RenderCommand::Type::SolidQuad;
        bot.pixel_rect = {
            px[0] - kBorder,
            px[1] + px[3],
            px[2] + 2.0f * kBorder,
            kBorder
        };
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

    // Visualize template extents in template preview window
    if (template_extents_[0] > 0.0f && template_extents_[1] > 0.0f) {
        const float win_h = static_cast<float>(GetHeight());
        const float unit_w = win_h * 16.0f / 9.0f;
        const float ext_w = template_extents_[0] * unit_w;
        const float ext_h = template_extents_[1] * win_h;
        constexpr float kExtBorder = 2.0f;

        RenderCommand ext_top;
        ext_top.type = RenderCommand::Type::SolidQuad;
        ext_top.pixel_rect = {0.0f, 0.0f, ext_w, kExtBorder};
        ext_top.color_rgba = {0.0f, 0.85f, 1.0f, 0.9f};
        batch.commands.push_back(ext_top);

        RenderCommand ext_bot;
        ext_bot.type = RenderCommand::Type::SolidQuad;
        ext_bot.pixel_rect = {0.0f, ext_h - kExtBorder, ext_w, kExtBorder};
        ext_bot.color_rgba = {0.0f, 0.85f, 1.0f, 0.9f};
        batch.commands.push_back(ext_bot);

        RenderCommand ext_left;
        ext_left.type = RenderCommand::Type::SolidQuad;
        ext_left.pixel_rect = {0.0f, 0.0f, kExtBorder, ext_h};
        ext_left.color_rgba = {0.0f, 0.85f, 1.0f, 0.9f};
        batch.commands.push_back(ext_left);

        RenderCommand ext_right;
        ext_right.type = RenderCommand::Type::SolidQuad;
        ext_right.pixel_rect = {ext_w - kExtBorder, 0.0f, kExtBorder, ext_h};
        ext_right.color_rgba = {0.0f, 0.85f, 1.0f, 0.9f};
        batch.commands.push_back(ext_right);
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
    const auto content_px_rect = RelativeToPixelRect(resolved_el.rect);
    const auto pad_px_rect = ComputePaddingPixelRect(
        resolved_el, content_px_rect);
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        resolved_el.font_size, static_cast<float>(GetHeight()));

    if (resolved_el.type != "team_scorecard" &&
        resolved_el.type != "game_scorecard" &&
        resolved_el.type != "team_roster") {
        GenerateBackgroundCommands(
            resolved_el.background,
            pad_px_rect,
            resolved_el.team_index,
            state,
            batch);
    }

    if (resolved_el.type == "user_text") {
        TextComponent::GenerateUserTextCommands(
            resolved_el,
            state,
            content_px_rect,
            static_cast<float>(GetHeight()),
            batch);
    } else if (resolved_el.type == "game_timer") {
        GenerateGameTimerCommands(resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "user_image" ||
               resolved_el.type == "image") {
        if (!resolved_el.image_file.empty()) {
            RenderCommand cmd;
            cmd.type = RenderCommand::Type::TexturedQuad;
            cmd.pixel_rect = content_px_rect;
            cmd.texture_asset = resolved_el.image_file;
            cmd.opacity = resolved_el.opacity;
            cmd.fit = resolved_el.fit.empty() ? "stretch" : resolved_el.fit;
            if (resolved_el.tint_team_color > 0.0f &&
                resolved_el.team_index > 0) {
                auto tit = state.teams.find(resolved_el.team_index);
                if (tit != state.teams.end()) {
                    cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                        tit->second.rgb, resolved_el.tint_team_color);
                }
            }
            batch.commands.push_back(cmd);
        }
    } else if (resolved_el.type == "movie" ||
               resolved_el.type == "user_movie") {
        if (!resolved_el.movie_file.empty()) {
            RenderCommand cmd;
            cmd.type = RenderCommand::Type::TexturedQuad;
            cmd.pixel_rect = content_px_rect;
            cmd.texture_asset = resolved_el.movie_file;
            cmd.opacity = resolved_el.opacity;
            cmd.fit = resolved_el.fit.empty() ? "stretch" : resolved_el.fit;
            cmd.is_movie = true;
            cmd.playback_speed = resolved_el.playback_speed;
            if (resolved_el.tint_team_color > 0.0f &&
                resolved_el.team_index > 0) {
                auto tit = state.teams.find(resolved_el.team_index);
                if (tit != state.teams.end()) {
                    cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                        tit->second.rgb, resolved_el.tint_team_color);
                }
            }
            batch.commands.push_back(cmd);
        }
    } else if (resolved_el.type == "team_scorecard") {
        int team_id = resolved_el.team_index;
        if (team_id <= 0) {
            for (const auto& [id, t] : state.teams) {
                if (!t.player_ids.empty()) {
                    team_id = id;
                    break;
                }
            }
        }
        if (team_id > 0) {
            GenerateTeamScorecardCommands(
                resolved_el, team_id, state, current_time_ms, batch);
        }
    } else if (resolved_el.type == "game_scorecard") {
        GenerateGameScorecardCommands(
            resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "team_roster") {
        int team_id = resolved_el.team_index;
        if (team_id <= 0) {
            for (const auto& [id, t] : state.teams) {
                if (!t.player_ids.empty()) {
                    team_id = id;
                    break;
                }
            }
        }
        if (team_id > 0) {
            GenerateTeamRosterCommands(
                resolved_el, team_id, state, current_time_ms, batch);
        }
    } else if (resolved_el.type == "event_scroller") {
        GenerateEventScrollerCommands(
            resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "important_game_messages" ||
               resolved_el.type == "messages_display") {
        GenerateImportantMessagesCommands(
            resolved_el, state, current_time_ms, batch);
    } else if (resolved_el.type == "player_profile_picture") {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = content_px_rect;
        std::string pic = resolved_el.image_file;
        if (pic.empty()) {
            for (const auto& [pid, p] : state.players) {
                if (!p.is_dummy && !p.picture_url.empty()) {
                    if (resolved_el.team_index <= 0 ||
                        p.team_id == resolved_el.team_index) {
                        pic = p.picture_url;
                        break;
                    }
                }
            }
        }
        if (pic.empty()) {
            pic = "assets/sm5/commander.png";
        }
        cmd.texture_asset = pic;
        cmd.opacity = resolved_el.opacity;
        cmd.fit = resolved_el.fit.empty() ? "stretch" : resolved_el.fit;
        if (resolved_el.tint_team_color > 0.0f &&
            resolved_el.team_index > 0) {
            auto tit = state.teams.find(resolved_el.team_index);
            if (tit != state.teams.end()) {
                cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                    tit->second.rgb, resolved_el.tint_team_color);
            }
        }
        batch.commands.push_back(cmd);
    } else if (resolved_el.type == "team_logo") {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = content_px_rect;
        cmd.texture_asset = resolved_el.image_file.empty()
            ? "assets/ball.png" : resolved_el.image_file;
        cmd.opacity = resolved_el.opacity;
        cmd.fit = resolved_el.fit.empty() ? "stretch" : resolved_el.fit;
        if (resolved_el.tint_team_color > 0.0f &&
            resolved_el.team_index > 0) {
            auto tit = state.teams.find(resolved_el.team_index);
            if (tit != state.teams.end()) {
                cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                    tit->second.rgb, resolved_el.tint_team_color);
            }
        }
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
            content_px_rect,
            static_cast<float>(GetHeight()),
            batch);
    }
}

void VisualizationWindow::GenerateBackgroundCommands(
    const BackgroundConfig& bg,
    const std::array<float, 4>& pixel_rect,
    int team_id,
    const GameStateSnapshot& state,
    RenderBatch& batch) const {
    if (!bg.enabled) {
        return;
    }

    const float win_h = static_cast<float>(GetHeight());
    const float scaled_radius =
        RichTextLayout::ComputePixelCornerRadius(bg.corner_radius, win_h);
    const float alpha = std::clamp(bg.opacity, 0.0f, 1.0f);

    std::string team_rgb;
    if (team_id > 0) {
        auto tit = state.teams.find(team_id);
        if (tit != state.teams.end()) {
            team_rgb = tit->second.rgb;
        }
    }

    // 1. Solid color background
    if (!bg.color.empty()) {
        auto rgba = ScorecardHelper::ParseHexColor(bg.color, 1.0f);
        rgba[3] *= alpha;
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::SolidQuad;
        cmd.pixel_rect = pixel_rect;
        cmd.color_rgba = rgba;
        cmd.corner_radius = scaled_radius;
        batch.commands.push_back(cmd);
    }

    // 2. Video background
    if (!bg.movie_file.empty()) {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = pixel_rect;
        cmd.texture_asset = bg.movie_file;
        cmd.opacity = alpha;
        cmd.fit = bg.fit.empty() ? "stretch" : bg.fit;
        cmd.is_movie = true;
        cmd.playback_speed = bg.playback_speed;
        cmd.corner_radius = scaled_radius;
        if (bg.tint_team_color > 0.0f && !team_rgb.empty()) {
            cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                team_rgb, bg.tint_team_color);
        }
        batch.commands.push_back(cmd);
    }

    // 3. Image background
    if (!bg.image_file.empty()) {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = pixel_rect;
        cmd.texture_asset = bg.image_file;
        cmd.opacity = alpha;
        cmd.fit = bg.fit.empty() ? "stretch" : bg.fit;
        cmd.corner_radius = scaled_radius;
        if (bg.tint_team_color > 0.0f && !team_rgb.empty()) {
            cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                team_rgb, bg.tint_team_color);
        }
        batch.commands.push_back(cmd);
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
    const float win_h = static_cast<float>(GetHeight());
    float row_height_px = 32.0f;
    const TemplateConfig* row_tmpl = FindTemplate(element.row_template_id);
    if (row_tmpl && row_tmpl->size[1] > 0.0f) {
        row_height_px = row_tmpl->size[1] * win_h;
    }

    const float scaled_spacing =
        RichTextLayout::ComputePixelVerticalSpacing(
            element.vertical_spacing, win_h);
    float height = 0.0f;

    const TemplateConfig* header_tmpl =
        FindTemplate(element.header_template_id);
    if (header_tmpl != nullptr && !header_tmpl->elements.empty()) {
        float header_height_px = row_height_px;
        if (header_tmpl->size[1] > 0.0f) {
            header_height_px = header_tmpl->size[1] * win_h;
        }
        height += header_height_px + 4.0f + scaled_spacing;
    }

    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, element.add_totals);

    if (!player_ids.empty()) {
        const float row_spacing = 2.0f + scaled_spacing;
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
    const auto pad_px_rect = ComputePaddingPixelRect(element, base_px_rect);
    GenerateBackgroundCommands(
        element.background, pad_px_rect, team_id, state, batch);

    const float win_h = static_cast<float>(GetHeight());
    const float unit_w = win_h * 16.0f / 9.0f;

    const TemplateConfig* header_tmpl =
        FindTemplate(element.header_template_id);
    const TemplateConfig* row_tmpl =
        FindTemplate(element.row_template_id);

    float row_height_px = 32.0f;
    float row_width_px = base_px_rect[2];
    if (row_tmpl && row_tmpl->size[1] > 0.0f) {
        row_height_px = row_tmpl->size[1] * win_h;
    }
    if (row_tmpl && row_tmpl->size[0] > 0.0f) {
        row_width_px = row_tmpl->size[0] * unit_w;
    }

    float header_height_px = row_height_px;
    float header_width_px = row_width_px;
    if (header_tmpl && header_tmpl->size[1] > 0.0f) {
        header_height_px = header_tmpl->size[1] * win_h;
    }
    if (header_tmpl && header_tmpl->size[0] > 0.0f) {
        header_width_px = header_tmpl->size[0] * unit_w;
    }

    float header_offset_x = 0.0f;
    float row_offset_x = 0.0f;
    if (element.alignment == "center") {
        header_offset_x = (base_px_rect[2] - header_width_px) / 2.0f;
        row_offset_x = (base_px_rect[2] - row_width_px) / 2.0f;
    } else if (element.alignment == "right") {
        header_offset_x = base_px_rect[2] - header_width_px;
        row_offset_x = base_px_rect[2] - row_width_px;
    }

    const float scaled_spacing =
        RichTextLayout::ComputePixelVerticalSpacing(
            element.vertical_spacing, win_h);
    float current_y = base_px_rect[1];

    // Optional header template
    if (header_tmpl != nullptr && !header_tmpl->elements.empty()) {
        for (const auto& hel : header_tmpl->elements) {
            std::array<float, 4> hp_rect{
                base_px_rect[0] + header_offset_x +
                    (hel.rect[0] * header_width_px),
                current_y + (hel.rect[1] * header_height_px),
                hel.rect[2] * header_width_px,
                hel.rect[3] * header_height_px
            };
            if (hel.type == "user_image" || hel.type == "image") {
                if (!hel.image_file.empty()) {
                    RenderCommand cmd;
                    cmd.type = RenderCommand::Type::TexturedQuad;
                    cmd.pixel_rect = hp_rect;
                    cmd.texture_asset = hel.image_file;
                    cmd.opacity = hel.opacity;
                    cmd.fit = hel.fit.empty() ? "stretch" : hel.fit;
                    if (hel.tint_team_color > 0.0f) {
                        cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                            team.rgb, hel.tint_team_color);
                    }
                    batch.commands.push_back(cmd);
                }
            } else if (hel.type == "movie" || hel.type == "user_movie") {
                if (!hel.movie_file.empty()) {
                    RenderCommand cmd;
                    cmd.type = RenderCommand::Type::TexturedQuad;
                    cmd.pixel_rect = hp_rect;
                    cmd.texture_asset = hel.movie_file;
                    cmd.opacity = hel.opacity;
                    cmd.fit = hel.fit.empty() ? "stretch" : hel.fit;
                    cmd.is_movie = true;
                    cmd.playback_speed = hel.playback_speed;
                    if (hel.tint_team_color > 0.0f) {
                        cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                            team.rgb, hel.tint_team_color);
                    }
                    batch.commands.push_back(cmd);
                }
            } else {
                TextComponent::GenerateCommands(
                    ResolveElementFont(hel),
                    hel.text.empty() ? "PLAYER" : hel.text,
                    hp_rect,
                    team.rgb,
                    false,
                    win_h,
                    batch);
            }
        }
        current_y += header_height_px + 4.0f + scaled_spacing;
    }

    const float start_players_y = current_y;

    // Sorted player rows
    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, element.add_totals);

    const std::string list_key =
        std::to_string(config_.id) + "_team_" + std::to_string(team_id);

    const float row_spacing = 2.0f + scaled_spacing;
    for (size_t row_idx = 0; row_idx < player_ids.size(); ++row_idx) {
        int pid = player_ids[row_idx];
        auto pit = state.players.find(pid);
        if (pit == state.players.end()) continue;
        const auto& player = pit->second;

        const float target_row_y = start_players_y +
            static_cast<float>(row_idx) * (row_height_px + row_spacing);

        const std::string player_anim =
            !element.player_change_animation.empty()
                ? element.player_change_animation
                : (!element.change_animation.empty()
                       ? element.change_animation
                       : "none");
        const float player_dur =
            element.player_animation_duration > 0.0f
                ? element.player_animation_duration
                : (element.animation_duration > 0.0f
                       ? element.animation_duration
                       : 0.5f);

        const float row_y = list_animation_tracker_.GetAnimatedPosition(
            list_key,
            pid,
            target_row_y,
            current_time_ms,
            player_anim,
            player_dur);

        if (row_tmpl != nullptr && !row_tmpl->elements.empty()) {
            for (const auto& rel : row_tmpl->elements) {
                std::array<float, 4> rpx_rect{
                    base_px_rect[0] + row_offset_x +
                        (rel.rect[0] * row_width_px),
                    row_y + (rel.rect[1] * row_height_px),
                    rel.rect[2] * row_width_px,
                    rel.rect[3] * row_height_px
                };
                if (rel.type == "user_image" || rel.type == "image") {
                    if (!rel.image_file.empty()) {
                        RenderCommand cmd;
                        cmd.type = RenderCommand::Type::TexturedQuad;
                        cmd.pixel_rect = rpx_rect;
                        cmd.texture_asset = rel.image_file;
                        cmd.opacity = rel.opacity;
                        cmd.fit = rel.fit.empty() ? "stretch" : rel.fit;
                        if (rel.tint_team_color > 0.0f) {
                            cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                                team.rgb, rel.tint_team_color);
                        }
                        batch.commands.push_back(cmd);
                    }
                } else if (rel.type == "movie" || rel.type == "user_movie") {
                    if (!rel.movie_file.empty()) {
                        RenderCommand cmd;
                        cmd.type = RenderCommand::Type::TexturedQuad;
                        cmd.pixel_rect = rpx_rect;
                        cmd.texture_asset = rel.movie_file;
                        cmd.opacity = rel.opacity;
                        cmd.fit = rel.fit.empty() ? "stretch" : rel.fit;
                        cmd.is_movie = true;
                        cmd.playback_speed = rel.playback_speed;
                        if (rel.tint_team_color > 0.0f) {
                            cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                                team.rgb, rel.tint_team_color);
                        }
                        batch.commands.push_back(cmd);
                    }
                } else {
                    TextComponent::GeneratePlayerElementCommands(
                        ResolveElementFont(rel),
                        player,
                        team.rgb,
                        rpx_rect,
                        win_h,
                        batch);
                }
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
    const auto pad_px_rect = ComputePaddingPixelRect(element, base_px_rect);
    GenerateBackgroundCommands(
        element.background, pad_px_rect, -1, state, batch);

    const float win_h = static_cast<float>(GetHeight());
    const std::string team_list_key =
        std::to_string(config_.id) + "_game_teams";

    const std::string team_anim =
        !element.team_change_animation.empty()
            ? element.team_change_animation
            : (!element.change_animation.empty()
                   ? element.change_animation
                   : "none");
    const float team_dur =
        element.team_animation_duration > 0.0f
            ? element.team_animation_duration
            : (element.animation_duration > 0.0f
                   ? element.animation_duration
                   : 0.5f);

    if (element.orientation == "horizontal") {
        const float section_width_rel =
            1.0f / static_cast<float>(team_ids.size());

        for (size_t i = 0; i < team_ids.size(); ++i) {
            ElementConfig sub_el = element;
            sub_el.team_index = team_ids[i];
            sub_el.background = element.team_background;
            const float target_rel_x =
                element.rect[0] +
                (static_cast<float>(i) * section_width_rel * element.rect[2]);
            const float anim_rel_x =
                list_animation_tracker_.GetAnimatedPosition(
                    team_list_key,
                    team_ids[i],
                    target_rel_x,
                    current_time_ms,
                    team_anim,
                    team_dur);
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
            sub_el.background = element.team_background;

            const float target_rel_y = curr_px_y / win_h;
            const float anim_rel_y =
                list_animation_tracker_.GetAnimatedPosition(
                    team_list_key,
                    team_ids[i],
                    target_rel_y,
                    current_time_ms,
                    team_anim,
                    team_dur);

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

            const float scaled_spacing =
                RichTextLayout::ComputePixelVerticalSpacing(
                    element.vertical_spacing, win_h);
            const float team_spacing_px = 16.0f + scaled_spacing;
            curr_px_y += team_h_px + team_spacing_px;
        }
    }
}

void VisualizationWindow::RenderPlayerProfileCard(
    const TemplateConfig* profile_tmpl,
    const PlayerSnapshot& player,
    const std::string& team_rgb,
    const std::array<float, 4>& card_px_rect,
    float win_h,
    RenderBatch& batch) const {
    if (!profile_tmpl || profile_tmpl->elements.empty()) {
        ElementConfig d_name;
        d_name.type = "player_name";
        d_name.font_size = 18.0f;
        std::array<float, 4> nrect{
            card_px_rect[0] + 4.0f,
            card_px_rect[1] + 2.0f,
            card_px_rect[2] - 8.0f,
            card_px_rect[3] * 0.5f
        };
        TextComponent::GeneratePlayerElementCommands(
            d_name, player, team_rgb, nrect, win_h, batch);
        return;
    }

    for (const auto& pel : profile_tmpl->elements) {
        std::array<float, 4> pel_rect{
            card_px_rect[0] + (pel.rect[0] * card_px_rect[2]),
            card_px_rect[1] + (pel.rect[1] * card_px_rect[3]),
            pel.rect[2] * card_px_rect[2],
            pel.rect[3] * card_px_rect[3]
        };

        if (pel.background.enabled) {
            const auto pel_pad = ComputePaddingRect(
                pel_rect, pel.padding, card_px_rect[2], card_px_rect[3]);
            GameStateSnapshot dummy_state;
            dummy_state.teams[player.team_id].rgb = team_rgb;
            GenerateBackgroundCommands(
                pel.background, pel_pad, player.team_id, dummy_state, batch);
        }

        if (pel.type == "user_image" || pel.type == "image") {
            if (!pel.image_file.empty()) {
                RenderCommand cmd;
                cmd.type = RenderCommand::Type::TexturedQuad;
                cmd.pixel_rect = pel_rect;
                cmd.texture_asset = pel.image_file;
                cmd.opacity = pel.opacity;
                cmd.fit = pel.fit.empty() ? "stretch" : pel.fit;
                if (pel.tint_team_color > 0.0f) {
                    cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                        team_rgb, pel.tint_team_color);
                }
                batch.commands.push_back(cmd);
            }
        } else if (pel.type == "movie" || pel.type == "user_movie") {
            if (!pel.movie_file.empty()) {
                RenderCommand cmd;
                cmd.type = RenderCommand::Type::TexturedQuad;
                cmd.pixel_rect = pel_rect;
                cmd.texture_asset = pel.movie_file;
                cmd.opacity = pel.opacity;
                cmd.fit = pel.fit.empty() ? "stretch" : pel.fit;
                cmd.is_movie = true;
                cmd.playback_speed = pel.playback_speed;
                if (pel.tint_team_color > 0.0f) {
                    cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                        team_rgb, pel.tint_team_color);
                }
                batch.commands.push_back(cmd);
            }
        } else if (pel.type == "player_profile_picture") {
            RenderCommand cmd;
            cmd.type = RenderCommand::Type::TexturedQuad;
            cmd.pixel_rect = pel_rect;
            std::string pic = !player.picture_url.empty()
                ? player.picture_url
                : (!pel.image_file.empty() ? pel.image_file : "assets/sm5/commander.png");
            cmd.texture_asset = pic;
            cmd.opacity = pel.opacity;
            cmd.fit = pel.fit.empty() ? "stretch" : pel.fit;
            if (pel.tint_team_color > 0.0f) {
                cmd.color_rgba = ScorecardHelper::ComputeTeamTint(
                    team_rgb, pel.tint_team_color);
            }
            batch.commands.push_back(cmd);
        } else {
            TextComponent::GeneratePlayerElementCommands(
                ResolveElementFont(pel),
                player,
                team_rgb,
                pel_rect,
                win_h,
                batch);
        }
    }
}

void VisualizationWindow::GenerateTeamRosterCommands(
    const ElementConfig& element,
    int team_id,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch) const {
    const auto it = state.teams.find(team_id);
    if (it == state.teams.end()) return;
    const auto& team = it->second;

    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const auto pad_px_rect = ComputePaddingPixelRect(element, base_px_rect);
    GenerateBackgroundCommands(
        element.background, pad_px_rect, team_id, state, batch);

    const PlayerSortOrder sort_order = (element.sort_order == "index")
        ? PlayerSortOrder::Index
        : PlayerSortOrder::Ranking;
    const auto player_ids = ScorecardHelper::GetSortedPlayerIds(
        state, team_id, sort_order, false);
    if (player_ids.empty()) return;

    const TemplateConfig* profile_tmpl =
        FindTemplate(element.player_profile_template_id);
    if (!profile_tmpl) {
        for (const auto& t : ui_config_.templates) {
            if (t.type == "player_profile") {
                profile_tmpl = &t;
                break;
            }
        }
    }

    const float win_h = static_cast<float>(GetHeight());
    const float unit_w = win_h * 16.0f / 9.0f;
    const float scaled_spacing =
        RichTextLayout::ComputePixelVerticalSpacing(
            element.vertical_spacing, win_h);
    const float item_spacing = scaled_spacing;

    float card_w = base_px_rect[2];
    float card_h = base_px_rect[3];
    if (profile_tmpl && profile_tmpl->size[0] > 0.0f &&
        profile_tmpl->size[1] > 0.0f) {
        card_w = profile_tmpl->size[0] * unit_w;
        card_h = profile_tmpl->size[1] * win_h;
    }

    const std::string anim_type =
        !element.player_change_animation.empty()
            ? element.player_change_animation
            : (!element.change_animation.empty()
                   ? element.change_animation
                   : "none");
    const float anim_dur =
        element.player_animation_duration > 0.0f
            ? element.player_animation_duration
            : (element.animation_duration > 0.0f
                   ? element.animation_duration
                   : 0.5f);
    const std::string list_key =
        std::to_string(config_.id) + "_roster_" + std::to_string(team_id);

    const size_t num_players = player_ids.size();
    if (element.orientation == "horizontal") {
        const float total_w = static_cast<float>(num_players) * card_w +
            (num_players > 1
                 ? static_cast<float>(num_players - 1) * item_spacing
                 : 0.0f);

        float offset_x = 0.0f;
        if (element.alignment == "center") {
            offset_x = (base_px_rect[2] - total_w) / 2.0f;
        } else if (element.alignment == "right") {
            offset_x = base_px_rect[2] - total_w;
        }

        for (size_t i = 0; i < num_players; ++i) {
            const int pid = player_ids[i];
            const auto pit = state.players.find(pid);
            if (pit == state.players.end()) continue;

            const float target_x = base_px_rect[0] + offset_x +
                static_cast<float>(i) * (card_w + item_spacing);
            const float anim_x = list_animation_tracker_.GetAnimatedPosition(
                list_key, pid, target_x, current_time_ms, anim_type, anim_dur);
            const std::array<float, 4> card_rect{
                anim_x, base_px_rect[1], card_w, card_h};
            RenderPlayerProfileCard(
                profile_tmpl, pit->second, team.rgb, card_rect, win_h, batch);
        }
    } else {
        const float total_h = static_cast<float>(num_players) * card_h +
            (num_players > 1
                 ? static_cast<float>(num_players - 1) * item_spacing
                 : 0.0f);

        float offset_x = 0.0f;
        if (element.alignment == "center") {
            offset_x = (base_px_rect[2] - card_w) / 2.0f;
        } else if (element.alignment == "right") {
            offset_x = base_px_rect[2] - card_w;
        }

        for (size_t i = 0; i < num_players; ++i) {
            const int pid = player_ids[i];
            const auto pit = state.players.find(pid);
            if (pit == state.players.end()) continue;

            const float target_y = base_px_rect[1] +
                static_cast<float>(i) * (card_h + item_spacing);
            const float anim_y = list_animation_tracker_.GetAnimatedPosition(
                list_key, pid, target_y, current_time_ms, anim_type, anim_dur);
            const std::array<float, 4> card_rect{
                base_px_rect[0] + offset_x, anim_y, card_w, card_h};
            RenderPlayerProfileCard(
                profile_tmpl, pit->second, team.rgb, card_rect, win_h, batch);
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
    const float scaled_spacing =
        RichTextLayout::ComputePixelVerticalSpacing(
            element.vertical_spacing, win_h);
    const float line_spacing = font_size_px * 0.15f + scaled_spacing;
    const float step_y = line_h + line_spacing;

    const size_t num_events = state.event_scroller.size();
    std::string scroller_key =
        std::to_string(element.z_position) + "_" +
        std::to_string(element.rect[0]) + "_" +
        std::to_string(element.rect[1]);

    const std::string anim_type =
        element.change_animation == "none" ? "none" :
        (element.change_animation == "linear" ? "linear" :
         "ease-in-and-ease-out");
    const float duration_s =
        element.animation_duration > 0.0f ? element.animation_duration : 0.5f;

    float y_scroll = event_scroller_tracker_.GetScrollOffset(
        scroller_key,
        num_events,
        step_y,
        current_time_ms,
        anim_type,
        duration_s);

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

void VisualizationWindow::GenerateImportantMessagesCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    int64_t current_time_ms,
    RenderBatch& batch
) const {
    const auto base_px_rect = RelativeToPixelRect(element.rect);
    const int num_lines = std::max(1, element.lines);
    const float display_time_s =
        element.display_time > 0.0f ? element.display_time : 4.0f;
    const float fadeout_time_s =
        element.fadeout_time >= 0.0f ? element.fadeout_time : 1.0f;

    std::string display_key =
        std::to_string(element.z_position) + "_" +
        std::to_string(element.rect[0]) + "_" +
        std::to_string(element.rect[1]);

    messages_display_tracker_.Update(
        display_key,
        state.important_events,
        num_lines,
        display_time_s,
        fadeout_time_s,
        current_time_ms);

    const auto& slots = messages_display_tracker_.GetSlots(display_key);
    const float win_h = static_cast<float>(GetHeight());
    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        element.font_size > 0.0f ? element.font_size : 20.0f, win_h);
    const float line_h = font_size_px * 1.4f;
    const float scaled_spacing =
        RichTextLayout::ComputePixelVerticalSpacing(
            element.vertical_spacing, win_h);

    float step_y = line_h + scaled_spacing;
    if (element.vertical_spacing == 0.0f && num_lines > 0) {
        float auto_slot_h = base_px_rect[3] / static_cast<float>(num_lines);
        if (auto_slot_h >= line_h) {
            step_y = auto_slot_h;
        }
    }

    ElementConfig line_el = element;
    line_el.font = (element.font.empty() || element.font == "default")
        ? ui_config_.default_font
        : element.font;
    line_el.font_size = element.font_size > 0.0f ? element.font_size : 20.0f;
    line_el.alignment =
        element.alignment.empty() ? "center" : element.alignment;
    line_el.color = element.color.empty() ? "#ffffff" : element.color;

    bool any_active = false;
    for (size_t i = 0; i < slots.size(); ++i) {
        if (!slots[i].active || slots[i].opacity <= 0.0f) {
            continue;
        }
        any_active = true;
        float y = base_px_rect[1] + static_cast<float>(i) * step_y;
        if (y + line_h < base_px_rect[1] ||
            y > base_px_rect[1] + base_px_rect[3]) {
            continue;
        }

        line_el.opacity = element.opacity * slots[i].opacity;
        TextComponent::GenerateCommands(
            line_el,
            slots[i].message,
            {base_px_rect[0], y, base_px_rect[2], line_h},
            line_el.color,
            false,
            win_h,
            batch,
            0.0f,
            base_px_rect,
            true);
    }
}

}  // namespace live_renderer

