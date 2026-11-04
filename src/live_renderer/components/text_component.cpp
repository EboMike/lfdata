#include "live_renderer/components/text_component.hpp"
#include <algorithm>
#include "live_renderer/components/scorecard_helper.hpp"

namespace live_renderer {

namespace {

void ReplaceAll(std::string& str, const std::string& from, const std::string& to) {
    if (from.empty()) return;
    size_t start_pos = 0;
    while ((start_pos = str.find(from, start_pos)) != std::string::npos) {
        str.replace(start_pos, from.length(), to);
        start_pos += to.length();
    }
}

}  // namespace

std::string TextComponent::ResolvePlayerText(
    std::string_view element_type,
    const PlayerSnapshot& player,
    std::string_view default_text) {
    if (element_type == "player_name") {
        return player.is_dummy ? "TOTALS" : player.name;
    }
    if (element_type == "player_score") {
        return std::to_string(player.score);
    }
    if (element_type == "player_lives") {
        return std::to_string(player.lives);
    }
    if (element_type == "player_ammo") {
        return std::to_string(player.shots);
    }
    if (element_type == "player_missiles") {
        return std::to_string(player.missiles);
    }
    if (element_type == "player_special_points") {
        return std::to_string(player.special_points);
    }
    if (element_type == "player_goals") {
        return std::to_string(player.goals);
    }
    if (element_type == "player_assists") {
        return std::to_string(player.assists);
    }
    if (element_type == "player_clears") {
        return std::to_string(player.clears);
    }
    if (element_type == "player_steals") {
        return std::to_string(player.steals);
    }
    if (element_type == "player_zaps") {
        return std::to_string(player.blocks);
    }
    if (element_type == "player_role") {
        return player.role;
    }

    if (!default_text.empty()) {
        std::string res(default_text);
        ReplaceAll(res, "{name}", player.is_dummy ? "TOTALS" : player.name);
        ReplaceAll(res, "{player_name}", player.is_dummy ? "TOTALS" : player.name);
        ReplaceAll(res, "{score}", std::to_string(player.score));
        ReplaceAll(res, "{lives}", std::to_string(player.lives));
        ReplaceAll(res, "{ammo}", std::to_string(player.shots));
        ReplaceAll(res, "{shots}", std::to_string(player.shots));
        ReplaceAll(res, "{missiles}", std::to_string(player.missiles));
        ReplaceAll(res, "{special_points}", std::to_string(player.special_points));
        ReplaceAll(res, "{role}", player.role);
        ReplaceAll(res, "{goals}", std::to_string(player.goals));
        ReplaceAll(res, "{assists}", std::to_string(player.assists));
        ReplaceAll(res, "{clears}", std::to_string(player.clears));
        ReplaceAll(res, "{steals}", std::to_string(player.steals));
        ReplaceAll(res, "{zaps}", std::to_string(player.blocks));
        return res;
    }

    return std::string(default_text);
}

void TextComponent::GenerateCommands(
    const ElementConfig& element,
    std::string_view raw_text,
    const std::array<float, 4>& pixel_rect,
    const std::string& base_color,
    bool rapid_fire,
    float window_height,
    RenderBatch& batch,
    float tilt_deg,
    const std::array<float, 4>& container_rect,
    bool clip_to_container) {
    if (raw_text.empty()) return;

    const float font_size_px = RichTextLayout::ComputePixelFontSize(
        element.font_size > 0.0f ? element.font_size : 20.0f,
        window_height);

    std::string color;
    if (!element.color.empty() && element.color != "#ffffff") {
        color = element.color;
    } else if (!base_color.empty()) {
        color = base_color;
    } else {
        color = "#ffffff";
    }

    const auto runs = RichTextLayout::ParseMarkup(raw_text, color);
    if (runs.empty()) return;

    // Fast-path: single plain text run
    if (runs.size() == 1 && !runs[0].is_image) {
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::Text;
        cmd.pixel_rect = pixel_rect;
        cmd.text = runs[0].text;
        cmd.font = element.font;
        cmd.hex_color = runs[0].hex_color;
        cmd.font_size_px = font_size_px;
        cmd.alignment = element.alignment.empty() ? "left" : element.alignment;
        cmd.black_outline = true;
        cmd.rapid_fire_effect = rapid_fire;
        cmd.tilt_deg = tilt_deg;
        cmd.container_rect = container_rect;
        cmd.clip_to_container = clip_to_container;
        batch.commands.push_back(cmd);
        return;
    }

    // Multi-run layout with inline images or multiple colors
    const float char_w = font_size_px * 0.60f;
    std::vector<float> run_widths;
    float total_width = 0.0f;

    for (const auto& run : runs) {
        float w = 0.0f;
        if (run.is_image) {
            w = font_size_px;
        } else {
            w = static_cast<float>(run.text.size()) * char_w;
        }
        run_widths.push_back(w);
        total_width += w;
    }

    float cur_x = pixel_rect[0];
    const std::string align = element.alignment.empty() ? "left" : element.alignment;
    if (align == "center") {
        cur_x += std::max(0.0f, (pixel_rect[2] - total_width) * 0.5f);
    } else if (align == "right") {
        cur_x += std::max(0.0f, pixel_rect[2] - total_width);
    }

    for (size_t i = 0; i < runs.size(); ++i) {
        const auto& run = runs[i];
        const float rw = run_widths[i];

        if (run.is_image) {
            RenderCommand icmd;
            icmd.type = RenderCommand::Type::TexturedQuad;
            icmd.pixel_rect = {
                cur_x,
                pixel_rect[1] + (pixel_rect[3] - font_size_px) * 0.5f,
                font_size_px,
                font_size_px
            };
            icmd.texture_asset = run.image_asset;
            icmd.opacity = element.opacity;
            icmd.tilt_deg = tilt_deg;
            icmd.container_rect = container_rect;
            icmd.clip_to_container = clip_to_container;
            batch.commands.push_back(icmd);
        } else if (!run.text.empty()) {
            RenderCommand tcmd;
            tcmd.type = RenderCommand::Type::Text;
            tcmd.pixel_rect = {cur_x, pixel_rect[1], rw, pixel_rect[3]};
            tcmd.text = run.text;
            tcmd.font = element.font;
            tcmd.hex_color = run.hex_color;
            tcmd.font_size_px = font_size_px;
            tcmd.alignment = "left";
            tcmd.black_outline = true;
            tcmd.rapid_fire_effect = rapid_fire;
            tcmd.tilt_deg = tilt_deg;
            tcmd.container_rect = container_rect;
            tcmd.clip_to_container = clip_to_container;
            batch.commands.push_back(tcmd);
        }

        cur_x += rw;
    }
}

void TextComponent::GenerateUserTextCommands(
    const ElementConfig& element,
    const GameStateSnapshot& state,
    const std::array<float, 4>& pixel_rect,
    float window_height,
    RenderBatch& batch) {
    const std::string text = RichTextLayout::SubstitutePlaceholders(element.text, state);
    GenerateCommands(
        element,
        text,
        pixel_rect,
        element.color,
        false,
        window_height,
        batch);
}

void TextComponent::GeneratePlayerElementCommands(
    const ElementConfig& element,
    const PlayerSnapshot& player,
    const std::string& team_color,
    const std::array<float, 4>& pixel_rect,
    float window_height,
    RenderBatch& batch) {
    // If element is player_role and has role icon without custom text, render role image
    if (element.type == "player_role" && !player.role.empty() && element.text.empty()) {
        const float font_size_px = RichTextLayout::ComputePixelFontSize(
            element.font_size > 0.0f ? element.font_size : 20.0f,
            window_height);
        RenderCommand cmd;
        cmd.type = RenderCommand::Type::TexturedQuad;
        cmd.pixel_rect = {
            pixel_rect[0],
            pixel_rect[1] + (pixel_rect[3] - font_size_px) * 0.5f,
            font_size_px,
            font_size_px
        };
        cmd.texture_asset = "assets/sm5/" + player.role + ".png";
        cmd.opacity = element.opacity;
        batch.commands.push_back(cmd);
        return;
    }

    const std::string state_color = ScorecardHelper::GetRowTextColor(player, team_color);
    const std::string text = ResolvePlayerText(element.type, player, element.text);

    GenerateCommands(
        element,
        text,
        pixel_rect,
        state_color,
        player.has_rapid_fire,
        window_height,
        batch);
}

}  // namespace live_renderer
