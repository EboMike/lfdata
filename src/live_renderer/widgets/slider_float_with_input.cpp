/**
 * @file slider_float_with_input.cpp
 * @brief Implementation of the composite slider and direct float input widget.
 */

#include "live_renderer/widgets/slider_float_with_input.hpp"
#include <algorithm>
#include <imgui.h>

namespace live_renderer {

bool SliderFloatWithInput::Render(
    const char* label,
    float* value,
    float v_min,
    float v_max,
    const char* unit_suffix) {
    if (!value) return false;

    ImGui::PushID(label);
    if (label && label[0]) {
        ImGui::TextUnformatted(label);
    }

    const float avail_w = ImGui::GetContentRegionAvail().x;
    const float unit_w = (unit_suffix && unit_suffix[0])
        ? ImGui::CalcTextSize(unit_suffix).x + 10.0f
        : 0.0f;
    const float input_w = 70.0f;
    const float spacing = ImGui::GetStyle().ItemSpacing.x;
    const float slider_w = std::max(
        60.0f, avail_w - input_w - unit_w - (spacing * 2.0f));

    bool modified = false;

    // 1. Slider without embedded text/unit
    ImGui::SetNextItemWidth(slider_w);
    if (ImGui::SliderFloat("##slider", value, v_min, v_max, "")) {
        modified = true;
    }

    // 2. Direct numeric text entry field taking a plain float value
    ImGui::SameLine();
    ImGui::SetNextItemWidth(input_w);
    if (ImGui::InputFloat("##input", value, 0.0f, 0.0f, "%.1f")) {
        *value = std::clamp(*value, v_min, v_max);
        modified = true;
    }

    // 3. Unit suffix displayed outside the text entry field
    if (unit_suffix && unit_suffix[0]) {
        ImGui::SameLine();
        ImGui::TextUnformatted(unit_suffix);
    }

    ImGui::PopID();
    return modified;
}

}  // namespace live_renderer

