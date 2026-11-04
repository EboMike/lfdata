#include "live_renderer/windows/element_property_inspector.hpp"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <vector>
#include <imgui.h>
#include "live_renderer/widgets/slider_float_with_input.hpp"

namespace live_renderer {

namespace {

void ParseHexToRgba(const std::string& hex, float rgba[4]) {
    rgba[0] = 1.0f;
    rgba[1] = 1.0f;
    rgba[2] = 1.0f;
    rgba[3] = 1.0f;
    if (hex.size() >= 7 && hex[0] == '#') {
        try {
            int r = std::stoi(hex.substr(1, 2), nullptr, 16);
            int g = std::stoi(hex.substr(3, 2), nullptr, 16);
            int b = std::stoi(hex.substr(5, 2), nullptr, 16);
            rgba[0] = r / 255.0f;
            rgba[1] = g / 255.0f;
            rgba[2] = b / 255.0f;
            if (hex.size() >= 9) {
                int a = std::stoi(hex.substr(7, 2), nullptr, 16);
                rgba[3] = a / 255.0f;
            }
        } catch (...) {}
    }
}

std::string RgbaToHex(const float rgba[4]) {
    char buf[16];
    int r = std::clamp(static_cast<int>(rgba[0] * 255.0f + 0.5f), 0, 255);
    int g = std::clamp(static_cast<int>(rgba[1] * 255.0f + 0.5f), 0, 255);
    int b = std::clamp(static_cast<int>(rgba[2] * 255.0f + 0.5f), 0, 255);
    std::snprintf(buf, sizeof(buf), "#%02x%02x%02x", r, g, b);
    return std::string(buf);
}

const char* const kAlignments[] = {"left", "center", "right"};
const char* const kOrientations[] = {"vertical", "horizontal"};
const char* const kSortOrders[] = {"ranking", "index"};

}  // namespace

void ElementPropertyInspector::Render(
    ElementConfig& element,
    const UIConfig& ui_config,
    const Callbacks& callbacks) {
    RenderHeaderAndActions(element, callbacks);
    ImGui::Spacing();
    RenderGeometryControls(element);
    ImGui::Spacing();
    RenderTextControls(element);
    ImGui::Spacing();
    RenderImageControls(element);
    ImGui::Spacing();
    RenderScorecardControls(element, ui_config);
    ImGui::Spacing();
    RenderScrollerControls(element);
}

void ElementPropertyInspector::RenderHeaderAndActions(
    const ElementConfig& element,
    const Callbacks& callbacks) {
    ImGui::TextColored(ImVec4(0.35f, 0.85f, 1.0f, 1.0f), "Element Properties: [%s]", element.type.c_str());
    ImGui::SameLine();

    if (ImGui::Button("Move Up##elem")) {
        if (callbacks.on_move_up) callbacks.on_move_up();
    }
    ImGui::SameLine();
    if (ImGui::Button("Move Down##elem")) {
        if (callbacks.on_move_down) callbacks.on_move_down();
    }
    ImGui::SameLine();

    ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.70f, 0.20f, 0.20f, 1.0f));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.85f, 0.25f, 0.25f, 1.0f));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.55f, 0.15f, 0.15f, 1.0f));
    if (ImGui::Button("Delete Element##elem")) {
        if (callbacks.on_delete) callbacks.on_delete();
    }
    ImGui::PopStyleColor(3);
}

void ElementPropertyInspector::RenderGeometryControls(ElementConfig& element) {
    if (ImGui::CollapsingHeader("Geometry / Bounds (0.0 to 1.0)", ImGuiTreeNodeFlags_DefaultOpen)) {
        float x = element.rect[0];
        float y = element.rect[1];
        float w = element.rect[2];
        float h = element.rect[3];

        bool changed = false;
        changed |= ImGui::DragFloat("X (rel)", &x, 0.005f, 0.0f, 1.0f, "%.3f");
        changed |= ImGui::DragFloat("Y (rel)", &y, 0.005f, 0.0f, 1.0f, "%.3f");
        changed |= ImGui::DragFloat("Width (rel)", &w, 0.005f, 0.005f, 1.0f, "%.3f");
        changed |= ImGui::DragFloat("Height (rel)", &h, 0.005f, 0.005f, 1.0f, "%.3f");

        if (changed) {
            element.rect[0] = std::clamp(x, 0.0f, 1.0f);
            element.rect[1] = std::clamp(y, 0.0f, 1.0f);
            element.rect[2] = std::clamp(w, 0.001f, 1.0f);
            element.rect[3] = std::clamp(h, 0.001f, 1.0f);
        }

        ImGui::InputInt("Z Position (Order)", &element.z_position);
    }
}

void ElementPropertyInspector::RenderTextControls(ElementConfig& element) {
    const bool is_textual = (
        element.type == "user_text" ||
        element.type == "game_timer" ||
        element.type == "event_scroller" ||
        element.type.rfind("player_", 0) == 0);

    if (!is_textual && element.text.empty() && element.font_size == 20.0f) {
        return;
    }

    if (ImGui::CollapsingHeader(
            "Text & Typography", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (element.type != "event_scroller") {
            char text_buf[512]{};
            std::snprintf(
                text_buf, sizeof(text_buf), "%s", element.text.c_str());
            if (ImGui::InputText(
                    "Text Content / Pattern", text_buf, sizeof(text_buf))) {
                element.text = text_buf;
            }
        }

        char font_buf[128]{};
        std::snprintf(font_buf, sizeof(font_buf), "%s", element.font.c_str());
        if (ImGui::InputText("Font", font_buf, sizeof(font_buf))) {
            element.font = font_buf;
        }

        ImGui::DragFloat(
            "Font Size", &element.font_size, 0.5f, 6.0f, 120.0f, "%.1f");

        int align_idx = 0;
        if (element.alignment == "center") align_idx = 1;
        else if (element.alignment == "right") align_idx = 2;

        if (ImGui::Combo(
                "Alignment", &align_idx, kAlignments,
                IM_ARRAYSIZE(kAlignments))) {
            element.alignment = kAlignments[align_idx];
        }

        float rgba[4]{};
        ParseHexToRgba(element.color, rgba);
        if (ImGui::ColorEdit3("Color", rgba)) {
            element.color = RgbaToHex(rgba);
        }

        char color_hex_buf[32]{};
        std::snprintf(
            color_hex_buf, sizeof(color_hex_buf), "%s",
            element.color.c_str());
        if (ImGui::InputText(
                "Hex Color Code", color_hex_buf, sizeof(color_hex_buf))) {
            element.color = color_hex_buf;
        }
    }
}

void ElementPropertyInspector::RenderImageControls(ElementConfig& element) {
    const bool is_image = (
        element.type == "user_image" ||
        element.type == "player_role" ||
        element.type == "player_profile_picture" ||
        element.type == "team_logo");

    if (!is_image && element.image_file.empty()) {
        return;
    }

    if (ImGui::CollapsingHeader("Image Asset", ImGuiTreeNodeFlags_DefaultOpen)) {
        char img_buf[512]{};
        std::snprintf(img_buf, sizeof(img_buf), "%s", element.image_file.c_str());
        if (ImGui::InputText("Image Path", img_buf, sizeof(img_buf))) {
            element.image_file = img_buf;
        }

        ImGui::SliderFloat("Opacity", &element.opacity, 0.0f, 1.0f, "%.2f");
    }
}

void ElementPropertyInspector::RenderScorecardControls(
    ElementConfig& element,
    const UIConfig& ui_config) {
    const bool is_container = (
        element.type == "team_scorecard" ||
        element.type == "game_scorecard" ||
        element.type == "team_roster");

    if (!is_container) return;

    if (ImGui::CollapsingHeader("Scorecard & Roster Settings", ImGuiTreeNodeFlags_DefaultOpen)) {
        int orient_idx = (element.orientation == "horizontal") ? 1 : 0;
        if (ImGui::Combo("Orientation", &orient_idx, kOrientations, IM_ARRAYSIZE(kOrientations))) {
            element.orientation = kOrientations[orient_idx];
        }

        int sort_idx = (element.sort_order == "index") ? 1 : 0;
        if (ImGui::Combo("Sort Order", &sort_idx, kSortOrders, IM_ARRAYSIZE(kSortOrders))) {
            element.sort_order = kSortOrders[sort_idx];
        }

        ImGui::Checkbox("Add Totals Row (Dummy Player)", &element.add_totals);

        ImGui::InputInt("Team Index (-1 for all)", &element.team_index);

        // Row template selection
        std::vector<std::pair<int, std::string>> row_tmpls;
        row_tmpls.push_back({-1, "None (-1)"});
        for (const auto& t : ui_config.templates) {
            if (t.type == "scorecard_row") {
                row_tmpls.push_back({t.id, "#" + std::to_string(t.id) + ": " + t.name});
            }
        }
        int cur_row_idx = 0;
        for (size_t i = 0; i < row_tmpls.size(); ++i) {
            if (row_tmpls[i].first == element.row_template_id) cur_row_idx = static_cast<int>(i);
        }
        std::vector<const char*> row_names;
        for (const auto& p : row_tmpls) row_names.push_back(p.second.c_str());
        if (ImGui::Combo("Row Template", &cur_row_idx, row_names.data(), static_cast<int>(row_names.size()))) {
            element.row_template_id = row_tmpls[cur_row_idx].first;
        }

        // Header template selection
        std::vector<std::pair<int, std::string>> header_tmpls;
        header_tmpls.push_back({-1, "None (-1)"});
        for (const auto& t : ui_config.templates) {
            if (t.type == "scorecard_header_row") {
                header_tmpls.push_back({t.id, "#" + std::to_string(t.id) + ": " + t.name});
            }
        }
        int cur_hdr_idx = 0;
        for (size_t i = 0; i < header_tmpls.size(); ++i) {
            if (header_tmpls[i].first == element.header_template_id) cur_hdr_idx = static_cast<int>(i);
        }
        std::vector<const char*> hdr_names;
        for (const auto& p : header_tmpls) hdr_names.push_back(p.second.c_str());
        if (ImGui::Combo("Header Template", &cur_hdr_idx, hdr_names.data(), static_cast<int>(hdr_names.size()))) {
            element.header_template_id = header_tmpls[cur_hdr_idx].first;
        }
    }
}

void ElementPropertyInspector::RenderScrollerControls(ElementConfig& element) {
    if (element.type != "event_scroller") return;

    if (ImGui::CollapsingHeader("Event Scroller Settings", ImGuiTreeNodeFlags_DefaultOpen)) {
        SliderFloatWithInput::Render(
            "Tilt Angle",
            &element.tilt,
            -45.0f,
            45.0f,
            "deg");
    }
}

}  // namespace live_renderer

