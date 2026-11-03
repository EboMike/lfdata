#include "live_renderer/windows/ui_editor_window.hpp"
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <imgui.h>
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/windows/ui_editor_constants.hpp"

namespace live_renderer {

UIEditorWindow::UIEditorWindow(UIConfig& ui_config, std::string ui_config_file)
    : ui_config_(ui_config),
      ui_config_file_(std::move(ui_config_file)) {
    if (ui_config_.windows.empty()) {
        WindowConfig default_win;
        default_win.id = 1;
        default_win.title = "Main Scoreboard Window";
        default_win.rect = {100, 100, 1280, 720};
        ui_config_.windows.push_back(default_win);
    }
}

void UIEditorWindow::SetCallbacks(Callbacks callbacks) {
    callbacks_ = std::move(callbacks);
}

void UIEditorWindow::SetActiveWindowIndex(int index) {
    if (ui_config_.windows.empty()) {
        active_window_index_ = 0;
        selected_element_index_ = -1;
        return;
    }
    if (index < 0) {
        active_window_index_ = static_cast<int>(ui_config_.windows.size()) - 1;
    } else if (index >= static_cast<int>(ui_config_.windows.size())) {
        active_window_index_ = 0;
    } else {
        active_window_index_ = index;
    }
    selected_element_index_ = -1;
    if (callbacks_.on_active_window_changed) {
        callbacks_.on_active_window_changed(active_window_index_);
    }
}

int UIEditorWindow::GenerateNextWindowId() const {
    int max_id = 0;
    for (const auto& w : ui_config_.windows) {
        if (w.id > max_id) max_id = w.id;
    }
    return max_id + 1;
}

int UIEditorWindow::GenerateNextTemplateId() const {
    int max_id = 0;
    for (const auto& t : ui_config_.templates) {
        if (t.id > max_id) max_id = t.id;
    }
    return max_id + 1;
}

std::vector<std::string> UIEditorWindow::GetAvailableElementTypes() const {
    std::vector<std::string> types;
    if (selected_template_id_ < 0) {
        for (const char* t : kTopLevelElementTypes) {
            types.push_back(t);
        }
        return types;
    }

    const auto it = std::find_if(
        ui_config_.templates.begin(),
        ui_config_.templates.end(),
        [this](const TemplateConfig& t) { return t.id == selected_template_id_; });

    if (it != ui_config_.templates.end()) {
        if (it->type == "scorecard_row") {
            for (const char* t : kScorecardRowElementTypes) types.push_back(t);
        } else if (it->type == "scorecard_header_row") {
            for (const char* t : kScorecardHeaderElementTypes) types.push_back(t);
        } else if (it->type == "player_profile") {
            for (const char* t : kPlayerProfileElementTypes) types.push_back(t);
        }
    }
    return types;
}

void UIEditorWindow::ClickNewWindow() {
    if (IsEditingTemplate()) return;
    std::snprintf(new_window_title_buf_, sizeof(new_window_title_buf_), "Window %d", GenerateNextWindowId());
    show_new_window_modal_ = true;
    pending_open_new_window_ = true;
}

bool UIEditorWindow::ConfirmNewWindow(const std::string& title) {
    if (title.empty()) {
        editor_error_message_ = "Window title cannot be empty.";
        return false;
    }
    WindowConfig win;
    win.id = GenerateNextWindowId();
    win.title = title;
    win.rect = {100, 100, 1280, 720};
    ui_config_.windows.push_back(win);
    SetActiveWindowIndex(static_cast<int>(ui_config_.windows.size()) - 1);

    show_new_window_modal_ = false;
    pending_open_new_window_ = false;
    editor_error_message_.clear();
    return true;
}

void UIEditorWindow::CancelNewWindow() {
    show_new_window_modal_ = false;
    pending_open_new_window_ = false;
    editor_error_message_.clear();
}

void UIEditorWindow::ClickNextWindow() {
    if (IsEditingTemplate() || ui_config_.windows.empty()) return;
    SetActiveWindowIndex(active_window_index_ + 1);
}

void UIEditorWindow::ClickPreviousWindow() {
    if (IsEditingTemplate() || ui_config_.windows.empty()) return;
    SetActiveWindowIndex(active_window_index_ - 1);
}

void UIEditorWindow::ClickAddElement() {
    add_element_type_index_ = 0;
    show_add_element_modal_ = true;
    pending_open_add_element_ = true;
}

bool UIEditorWindow::ConfirmAddElement(const std::string& type_name) {
    if (type_name.empty()) return false;

    ElementConfig el;
    el.type = type_name;
    el.rect = {0.05f, 0.05f, 0.40f, 0.10f};

    if (selected_template_id_ < 0) {
        if (active_window_index_ >= 0 && active_window_index_ < static_cast<int>(ui_config_.windows.size())) {
            ui_config_.windows[active_window_index_].elements.push_back(el);
            selected_element_index_ = static_cast<int>(ui_config_.windows[active_window_index_].elements.size()) - 1;
        }
    } else {
        auto it = std::find_if(
            ui_config_.templates.begin(),
            ui_config_.templates.end(),
            [this](const TemplateConfig& t) { return t.id == selected_template_id_; });
        if (it != ui_config_.templates.end()) {
            it->elements.push_back(el);
            selected_element_index_ = static_cast<int>(it->elements.size()) - 1;
        }
    }

    show_add_element_modal_ = false;
    pending_open_add_element_ = false;
    editor_error_message_.clear();
    return true;
}

void UIEditorWindow::CancelAddElement() {
    show_add_element_modal_ = false;
    pending_open_add_element_ = false;
    editor_error_message_.clear();
}

void UIEditorWindow::ClickNewTemplate() {
    if (IsEditingTemplate()) return;
    std::snprintf(new_template_name_buf_, sizeof(new_template_name_buf_), "Template %d", GenerateNextTemplateId());
    new_template_type_index_ = 0;
    show_new_template_modal_ = true;
    pending_open_new_template_ = true;
}

bool UIEditorWindow::ConfirmNewTemplate(const std::string& name, const std::string& type) {
    if (name.empty()) {
        editor_error_message_ = "Template name cannot be empty.";
        return false;
    }
    TemplateConfig tmpl;
    tmpl.id = GenerateNextTemplateId();
    tmpl.name = name;
    tmpl.type = type;
    tmpl.size = {1.0f, 0.05f};
    ui_config_.templates.push_back(tmpl);

    SelectTemplateForEditing(tmpl.id);

    show_new_template_modal_ = false;
    pending_open_new_template_ = false;
    editor_error_message_.clear();
    return true;
}

void UIEditorWindow::CancelNewTemplate() {
    show_new_template_modal_ = false;
    pending_open_new_template_ = false;
    editor_error_message_.clear();
}

void UIEditorWindow::SelectTemplateForEditing(int template_id) {
    selected_template_id_ = template_id;
    selected_element_index_ = -1;
    if (callbacks_.on_active_template_changed) {
        callbacks_.on_active_template_changed(selected_template_id_);
    }
}

void UIEditorWindow::DoneWithTemplate() {
    selected_template_id_ = -1;
    selected_element_index_ = -1;
    if (callbacks_.on_active_template_changed) {
        callbacks_.on_active_template_changed(-1);
    }
}

bool UIEditorWindow::ClickSaveAndBack() {
    if (IsEditingTemplate()) {
        DoneWithTemplate();
        return true;
    }

    if (!ui_config_file_.empty()) {
        ConfigSerializer::SaveUIConfig(ui_config_file_, ui_config_);
    }

    if (callbacks_.on_save_and_back) {
        callbacks_.on_save_and_back();
    }
    return true;
}

void UIEditorWindow::RenderImGui() {
    const ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);

    constexpr ImGuiWindowFlags kWindowFlags =
        ImGuiWindowFlags_NoDecoration |
        ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings;

    if (ImGui::Begin("UI Editor Control", nullptr, kWindowFlags)) {
        RenderTopControls();
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();
        RenderTemplatesListBox();
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();
        RenderActiveDetails();
        RenderModals();
    }
    ImGui::End();
}

void UIEditorWindow::RenderTopControls() {
    const bool template_mode = IsEditingTemplate();
    const float button_width = (ImGui::GetContentRegionAvail().x - 20.0f) / 3.0f;
    const ImVec2 btn_size(button_width, 32.0f);

    if (template_mode) {
        ImGui::BeginDisabled();
    }
    if (ImGui::Button("New window", btn_size)) {
        ClickNewWindow();
    }
    ImGui::SameLine();
    if (ImGui::Button("Previous", btn_size)) {
        ClickPreviousWindow();
    }
    ImGui::SameLine();
    if (ImGui::Button("Next", btn_size)) {
        ClickNextWindow();
    }
    if (template_mode) {
        ImGui::EndDisabled();
    }

    ImGui::Spacing();

    if (ImGui::Button("Add element", btn_size)) {
        ClickAddElement();
    }
    ImGui::SameLine();

    if (template_mode) {
        ImGui::BeginDisabled();
    }
    if (ImGui::Button("New template", btn_size)) {
        ClickNewTemplate();
    }
    if (template_mode) {
        ImGui::EndDisabled();
    }
    ImGui::SameLine();

    const char* save_btn_text = template_mode ? "Done with template" : "Save & Back";
    if (ImGui::Button(save_btn_text, btn_size)) {
        ClickSaveAndBack();
    }
}

void UIEditorWindow::RenderTemplatesListBox() {
    ImGui::TextUnformatted("Templates:");
    ImGui::SameLine();
    if (IsEditingTemplate()) {
        ImGui::TextColored(ImVec4(0.3f, 0.8f, 1.0f, 1.0f), "[Editing Template Mode]");
    } else {
        ImGui::TextDisabled("(Click template to edit its layout)");
    }

    if (ImGui::BeginListBox("##templates_list", ImVec2(-FLT_MIN, 90.0f))) {
        for (const auto& tmpl : ui_config_.templates) {
            const bool is_selected = (selected_template_id_ == tmpl.id);
            char label[256];
            std::snprintf(label, sizeof(label), "#%d: %s (%s) [%zu elements]",
                          tmpl.id, tmpl.name.c_str(), tmpl.type.c_str(), tmpl.elements.size());
            if (ImGui::Selectable(label, is_selected)) {
                SelectTemplateForEditing(tmpl.id);
            }
        }
        ImGui::EndListBox();
    }
}

void UIEditorWindow::RenderActiveDetails() {
    if (IsEditingTemplate()) {
        auto it = std::find_if(
            ui_config_.templates.begin(),
            ui_config_.templates.end(),
            [this](const TemplateConfig& t) { return t.id == selected_template_id_; });
        if (it != ui_config_.templates.end()) {
            ImGui::Text("Active Template: #%d - %s", it->id, it->name.c_str());
            ImGui::Text("Type: %s | Size: [%.2f, %.2f] | Elements: %zu",
                        it->type.c_str(), it->size[0], it->size[1], it->elements.size());
        }
    } else {
        if (active_window_index_ >= 0 && active_window_index_ < static_cast<int>(ui_config_.windows.size())) {
            const auto& win = ui_config_.windows[active_window_index_];
            ImGui::Text("Active Window (%d/%zu): #%d - %s",
                        active_window_index_ + 1, ui_config_.windows.size(), win.id, win.title.c_str());
            ImGui::Text("Resolution: %dx%d (at %d,%d) | Elements: %zu",
                        win.rect[2], win.rect[3], win.rect[0], win.rect[1], win.elements.size());
        } else {
            ImGui::TextUnformatted("No windows configured.");
        }
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    RenderElementsListBox();

    if (selected_element_index_ >= 0) {
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();
        RenderSelectedElementInspector();
    }
}

void UIEditorWindow::RenderModals() {
    if (pending_open_new_window_) {
        ImGui::OpenPopup("New Window");
        pending_open_new_window_ = false;
    }
    if (ImGui::BeginPopupModal("New Window", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::TextUnformatted("Window Title:");
        ImGui::SetNextItemWidth(300.0f);
        ImGui::InputText("##win_title", new_window_title_buf_, sizeof(new_window_title_buf_));

        if (!editor_error_message_.empty()) {
            ImGui::Spacing();
            ImGui::TextColored(ImVec4(0.95f, 0.30f, 0.25f, 1.0f), "%s", editor_error_message_.c_str());
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Create", ImVec2(120.0f, 0.0f))) {
            if (ConfirmNewWindow(new_window_title_buf_)) {
                ImGui::CloseCurrentPopup();
            }
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelNewWindow();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    if (pending_open_new_template_) {
        ImGui::OpenPopup("New Template");
        pending_open_new_template_ = false;
    }
    if (ImGui::BeginPopupModal("New Template", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::TextUnformatted("Template Name:");
        ImGui::SetNextItemWidth(300.0f);
        ImGui::InputText("##tmpl_name", new_template_name_buf_, sizeof(new_template_name_buf_));

        ImGui::TextUnformatted("Template Type:");
        ImGui::SetNextItemWidth(300.0f);
        ImGui::Combo("##tmpl_type", &new_template_type_index_, kTemplateTypes, IM_ARRAYSIZE(kTemplateTypes));

        if (!editor_error_message_.empty()) {
            ImGui::Spacing();
            ImGui::TextColored(ImVec4(0.95f, 0.30f, 0.25f, 1.0f), "%s", editor_error_message_.c_str());
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Create", ImVec2(120.0f, 0.0f))) {
            if (ConfirmNewTemplate(new_template_name_buf_, kTemplateTypes[new_template_type_index_])) {
                ImGui::CloseCurrentPopup();
            }
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelNewTemplate();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    if (pending_open_add_element_) {
        ImGui::OpenPopup("Add Element");
        pending_open_add_element_ = false;
    }
    if (ImGui::BeginPopupModal("Add Element", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        auto avail_types = GetAvailableElementTypes();
        ImGui::TextUnformatted("Select Element Type:");
        if (avail_types.empty()) {
            ImGui::TextDisabled("No elements available for this context.");
        } else {
            std::vector<const char*> type_ptrs;
            for (const auto& t : avail_types) {
                type_ptrs.push_back(t.c_str());
            }
            if (add_element_type_index_ >= static_cast<int>(type_ptrs.size())) {
                add_element_type_index_ = 0;
            }
            ImGui::SetNextItemWidth(300.0f);
            ImGui::Combo("##el_type", &add_element_type_index_, type_ptrs.data(), static_cast<int>(type_ptrs.size()));
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (!avail_types.empty()) {
            if (ImGui::Button("Add", ImVec2(120.0f, 0.0f))) {
                if (ConfirmAddElement(avail_types[add_element_type_index_])) {
                    ImGui::CloseCurrentPopup();
                }
            }
            ImGui::SameLine();
        }
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelAddElement();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }
}

}  // namespace live_renderer
