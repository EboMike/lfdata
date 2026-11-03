#ifndef LIVE_RENDERER_WINDOWS_UI_EDITOR_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_UI_EDITOR_WINDOW_HPP_

#include <functional>
#include <string>
#include <vector>
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Control window active during UI Editor Mode.
 *
 * Replaces the main control window when editing layouts.
 * Supports window navigation, creating windows/templates, adding elements,
 * template-specific editing mode, and saving UI configuration back.
 */
class UIEditorWindow {
public:
    struct Callbacks {
        std::function<void()> on_save_and_back;
        std::function<void(int window_index)> on_active_window_changed;
        std::function<void(int template_id)> on_active_template_changed;
    };

    explicit UIEditorWindow(UIConfig& ui_config, std::string ui_config_file = "");
    ~UIEditorWindow() = default;

    void SetCallbacks(Callbacks callbacks);
    void SetUIConfigFile(const std::string& path) { ui_config_file_ = path; }
    const std::string& GetUIConfigFile() const { return ui_config_file_; }

    /**
     * @brief Renders the UI Editor Control interface using Dear ImGui.
     */
    void RenderImGui();

    // Editor actions
    void ClickNewWindow();
    bool ConfirmNewWindow(const std::string& title);
    void CancelNewWindow();

    void ClickNextWindow();
    void ClickPreviousWindow();

    void ClickAddElement();
    bool ConfirmAddElement(const std::string& type_name);
    void CancelAddElement();

    void ClickNewTemplate();
    bool ConfirmNewTemplate(const std::string& name, const std::string& type);
    void CancelNewTemplate();

    void SelectTemplateForEditing(int template_id);
    void DoneWithTemplate();

    bool ClickSaveAndBack();

    // State queries
    int GetActiveWindowIndex() const { return active_window_index_; }
    void SetActiveWindowIndex(int index);

    int GetSelectedTemplateId() const { return selected_template_id_; }
    bool IsEditingTemplate() const { return selected_template_id_ >= 0; }

    bool IsNewWindowModalOpen() const { return show_new_window_modal_; }
    bool IsNewTemplateModalOpen() const { return show_new_template_modal_; }
    bool IsAddElementModalOpen() const { return show_add_element_modal_; }

    // Helpers for element types allowed in current context
    std::vector<std::string> GetAvailableElementTypes() const;

private:
    void RenderTopControls();
    void RenderTemplatesListBox();
    void RenderActiveDetails();
    void RenderModals();

    int GenerateNextWindowId() const;
    int GenerateNextTemplateId() const;

    UIConfig& ui_config_;
    std::string ui_config_file_;
    Callbacks callbacks_;

    int active_window_index_ = 0;
    int selected_template_id_ = -1; // -1 means viewing/editing windows

    // Modals state
    bool show_new_window_modal_ = false;
    bool pending_open_new_window_ = false;
    char new_window_title_buf_[256]{};

    bool show_new_template_modal_ = false;
    bool pending_open_new_template_ = false;
    char new_template_name_buf_[256]{};
    int new_template_type_index_ = 0;

    bool show_add_element_modal_ = false;
    bool pending_open_add_element_ = false;
    int add_element_type_index_ = 0;

    std::string editor_error_message_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_UI_EDITOR_WINDOW_HPP_

