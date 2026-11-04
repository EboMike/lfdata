#include "live_renderer/windows/ui_editor_window.hpp"
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <string>
#include <vector>
#include <imgui.h>

namespace live_renderer {

std::vector<ElementConfig>& UIEditorWindow::GetActiveElements() {
    static std::vector<ElementConfig> empty_elements;
    if (selected_template_id_ >= 0) {
        auto it = std::find_if(
            ui_config_.templates.begin(),
            ui_config_.templates.end(),
            [this](const TemplateConfig& t) { return t.id == selected_template_id_; });
        if (it != ui_config_.templates.end()) {
            return it->elements;
        }
        return empty_elements;
    }
    if (active_window_index_ >= 0 && active_window_index_ < static_cast<int>(ui_config_.windows.size())) {
        return ui_config_.windows[active_window_index_].elements;
    }
    return empty_elements;
}

const std::vector<ElementConfig>& UIEditorWindow::GetActiveElements() const {
    static const std::vector<ElementConfig> empty_elements;
    if (selected_template_id_ >= 0) {
        auto it = std::find_if(
            ui_config_.templates.begin(),
            ui_config_.templates.end(),
            [this](const TemplateConfig& t) { return t.id == selected_template_id_; });
        if (it != ui_config_.templates.end()) {
            return it->elements;
        }
        return empty_elements;
    }
    if (active_window_index_ >= 0 && active_window_index_ < static_cast<int>(ui_config_.windows.size())) {
        return ui_config_.windows[active_window_index_].elements;
    }
    return empty_elements;
}

void UIEditorWindow::SetSelectedElementIndex(int index) {
    const auto& elements = GetActiveElements();
    if (index >= 0 && index < static_cast<int>(elements.size())) {
        selected_element_index_ = index;
    } else {
        selected_element_index_ = -1;
    }
}

ElementConfig* UIEditorWindow::GetSelectedElement() {
    auto& elements = GetActiveElements();
    if (selected_element_index_ >= 0 && selected_element_index_ < static_cast<int>(elements.size())) {
        return &elements[selected_element_index_];
    }
    return nullptr;
}

const ElementConfig* UIEditorWindow::GetSelectedElement() const {
    const auto& elements = GetActiveElements();
    if (selected_element_index_ >= 0 && selected_element_index_ < static_cast<int>(elements.size())) {
        return &elements[selected_element_index_];
    }
    return nullptr;
}

void UIEditorWindow::DeleteSelectedElement() {
    auto& elements = GetActiveElements();
    if (selected_element_index_ < 0 || selected_element_index_ >= static_cast<int>(elements.size())) {
        return;
    }
    elements.erase(elements.begin() + selected_element_index_);
    if (elements.empty()) {
        selected_element_index_ = -1;
    } else if (selected_element_index_ >= static_cast<int>(elements.size())) {
        selected_element_index_ = static_cast<int>(elements.size()) - 1;
    }
}

void UIEditorWindow::MoveSelectedElementUp() {
    auto& elements = GetActiveElements();
    if (selected_element_index_ > 0 && selected_element_index_ < static_cast<int>(elements.size())) {
        std::swap(elements[selected_element_index_], elements[selected_element_index_ - 1]);
        selected_element_index_--;
    }
}

void UIEditorWindow::MoveSelectedElementDown() {
    auto& elements = GetActiveElements();
    if (selected_element_index_ >= 0 && selected_element_index_ + 1 < static_cast<int>(elements.size())) {
        std::swap(elements[selected_element_index_], elements[selected_element_index_ + 1]);
        selected_element_index_++;
    }
}

void UIEditorWindow::RenderElementsListBox() {
    const auto& elements = GetActiveElements();
    if (IsEditingTemplate()) {
        ImGui::TextUnformatted("Elements in Current Template:");
    } else {
        ImGui::TextUnformatted("Elements in Current Window:");
    }
    ImGui::SameLine();
    ImGui::TextDisabled("(Click element to inspect and edit)");

    if (elements.empty()) {
        ImGui::TextDisabled("No elements configured. Click 'Add element' above to add one.");
        return;
    }

    if (ImGui::BeginListBox("##elements_list", ImVec2(-FLT_MIN, 110.0f))) {
        for (int i = 0; i < static_cast<int>(elements.size()); ++i) {
            const auto& el = elements[i];
            const bool is_selected = (selected_element_index_ == i);
            char label[256];
            std::string extra_info;
            if (!el.text.empty()) {
                extra_info = " \"" + el.text.substr(0, 18) + (el.text.size() > 18 ? "..." : "") + "\"";
            } else if (!el.image_file.empty()) {
                extra_info = " [" + el.image_file + "]";
            } else if (!el.movie_file.empty()) {
                extra_info = " [" + el.movie_file + "]";
            }
            std::snprintf(label, sizeof(label), "#%d: %s (%.2f, %.2f, %.2f, %.2f)%s",
                          i + 1, el.type.c_str(), el.rect[0], el.rect[1], el.rect[2], el.rect[3], extra_info.c_str());
            if (ImGui::Selectable(label, is_selected)) {
                selected_element_index_ = i;
            }
        }
        ImGui::EndListBox();
    }
}

void UIEditorWindow::RenderSelectedElementInspector() {
    auto* el = GetSelectedElement();
    if (!el) return;

    if (!ui_config_file_.empty()) {
        std::filesystem::path p(ui_config_file_);
        property_inspector_.SetConfigDirectory(
            p.has_parent_path() ? p.parent_path().string() : ".");
    }

    property_inspector_.Render(
        *el,
        ui_config_,
        ElementPropertyInspector::Callbacks{
            [this]() { DeleteSelectedElement(); },
            [this]() { MoveSelectedElementUp(); },
            [this]() { MoveSelectedElementDown(); }
        });
}

}  // namespace live_renderer

