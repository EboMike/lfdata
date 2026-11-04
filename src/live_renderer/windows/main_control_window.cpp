#include "live_renderer/windows/main_control_window.hpp"
#include <cstdio>
#include <cstring>
#include <imgui.h>
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/version.hpp"

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
#endif

namespace live_renderer {

namespace {
constexpr const char* kAppName = "LF Live Renderer";
constexpr const char* kAppAuthor = "EboMike";
}  // namespace

const char* MainControlWindow::GetApplicationName() {
    return kAppName;
}

const char* MainControlWindow::GetApplicationVersion() {
    return kLiveRendererVersion;
}

const char* MainControlWindow::GetApplicationAuthor() {
    return kAppAuthor;
}

MainControlWindow::MainControlWindow(
    const std::string& global_config_path,
    GlobalConfig& global_config,
    UIConfig& ui_config,
    LiveStateStore& state_store,
    TcpConsumerClient& client)
    : global_config_path_(global_config_path),
      global_config_(global_config),
      ui_config_(ui_config),
      state_store_(state_store),
      client_(client),
      draft_settings_(global_config) {
    std::snprintf(open_config_path_buf_, sizeof(open_config_path_buf_), "%s", global_config_path_.c_str());
    std::snprintf(settings_host_buf_, sizeof(settings_host_buf_), "%s", global_config_.host.c_str());
    settings_port_ = global_config_.port;
    std::snprintf(settings_ui_file_buf_, sizeof(settings_ui_file_buf_), "%s", global_config_.ui_config_file.c_str());
}

void MainControlWindow::SetCallbacks(Callbacks callbacks) {
    callbacks_ = std::move(callbacks);
}

ConnectionStatus MainControlWindow::GetConnectionStatus() const {
    return client_.GetStatus();
}

std::string MainControlWindow::GetConnectionStatusText() const {
    const std::string endpoint = client_.GetHost() + ":" + std::to_string(client_.GetPort());
    switch (client_.GetStatus()) {
        case ConnectionStatus::Connected:
            return "Connected (" + endpoint + ")";
        case ConnectionStatus::Connecting:
            return "Connecting (" + endpoint + ")...";
        case ConnectionStatus::Disconnected:
        default:
            return "Disconnected (" + endpoint + ")";
    }
}

std::array<float, 4> MainControlWindow::GetConnectionStatusColor() const {
    switch (client_.GetStatus()) {
        case ConnectionStatus::Connected:
            return {0.18f, 0.80f, 0.44f, 1.0f};  // Green
        case ConnectionStatus::Connecting:
            return {0.95f, 0.61f, 0.07f, 1.0f};  // Amber
        case ConnectionStatus::Disconnected:
        default:
            return {0.91f, 0.30f, 0.24f, 1.0f};  // Red
    }
}

void MainControlWindow::ClickReconnect() {
    state_store_.ClearState();
    client_.Reconnect();
    if (callbacks_.on_reconnect) {
        callbacks_.on_reconnect();
    }
}

void MainControlWindow::ClickUIEditor() {
    in_ui_editor_mode_ = true;
    if (callbacks_.on_enter_ui_editor) {
        callbacks_.on_enter_ui_editor();
    }
}

void MainControlWindow::ClickQuit() {
    show_quit_confirm_modal_ = true;
    pending_open_quit_modal_ = true;
}

void MainControlWindow::ConfirmQuit() {
    show_quit_confirm_modal_ = false;
    pending_open_quit_modal_ = false;
    quit_confirmed_ = true;
}

void MainControlWindow::CancelQuit() {
    show_quit_confirm_modal_ = false;
    pending_open_quit_modal_ = false;
}

void MainControlWindow::OpenConfigurationDialog() {
    modal_error_message_.clear();
    std::snprintf(open_config_path_buf_, sizeof(open_config_path_buf_), "%s", global_config_path_.c_str());
    show_open_config_modal_ = true;
    pending_open_config_modal_ = true;
}

bool MainControlWindow::ConfirmOpenConfiguration(const std::string& new_config_path) {
    if (new_config_path.empty()) {
        modal_error_message_ = "Configuration file path cannot be empty.";
        return false;
    }

    GlobalConfig loaded_global;
    if (!ConfigSerializer::LoadGlobalConfig(new_config_path, loaded_global)) {
        modal_error_message_ = "Failed to load configuration file: " + new_config_path;
        return false;
    }

    global_config_path_ = new_config_path;
    global_config_ = loaded_global;

    UIConfig loaded_ui;
    if (ConfigSerializer::LoadUIConfig(global_config_.ui_config_file, loaded_ui)) {
        ui_config_ = loaded_ui;
    } else {
        ui_config_ = UIConfig{};
    }

    // Reset entire program state and reconnect to configured server
    in_ui_editor_mode_ = false;
    state_store_.ClearState();
    client_.UpdateTarget(global_config_.host, global_config_.port);

    if (callbacks_.on_open_configuration) {
        callbacks_.on_open_configuration(new_config_path);
    }

    modal_error_message_.clear();
    show_open_config_modal_ = false;
    pending_open_config_modal_ = false;
    return true;
}

void MainControlWindow::CancelOpenConfiguration() {
    modal_error_message_.clear();
    show_open_config_modal_ = false;
    pending_open_config_modal_ = false;
}

void MainControlWindow::OpenSettingsDialog() {
    modal_error_message_.clear();
    draft_settings_ = global_config_;
    std::snprintf(settings_host_buf_, sizeof(settings_host_buf_), "%s", draft_settings_.host.c_str());
    settings_port_ = draft_settings_.port;
    std::snprintf(settings_ui_file_buf_, sizeof(settings_ui_file_buf_), "%s", draft_settings_.ui_config_file.c_str());
    show_settings_modal_ = true;
    pending_open_settings_modal_ = true;
}

void MainControlWindow::SetDraftSettings(const std::string& host, int port, const std::string& ui_config_file) {
    draft_settings_.host = host;
    draft_settings_.port = port;
    draft_settings_.ui_config_file = ui_config_file;
    std::snprintf(settings_host_buf_, sizeof(settings_host_buf_), "%s", host.c_str());
    settings_port_ = port;
    std::snprintf(settings_ui_file_buf_, sizeof(settings_ui_file_buf_), "%s", ui_config_file.c_str());
}

bool MainControlWindow::SaveSettingsDialog() {
    draft_settings_.host = settings_host_buf_;
    draft_settings_.port = settings_port_;
    draft_settings_.ui_config_file = settings_ui_file_buf_;

    if (draft_settings_.host.empty()) {
        modal_error_message_ = "Server IP / Host cannot be empty.";
        return false;
    }
    if (draft_settings_.port <= 0 || draft_settings_.port > 65535) {
        modal_error_message_ = "Consumer Port must be between 1 and 65535.";
        return false;
    }
    if (draft_settings_.ui_config_file.empty()) {
        modal_error_message_ = "UI Configuration File cannot be empty.";
        return false;
    }

    if (!ConfigSerializer::SaveGlobalConfig(global_config_path_, draft_settings_)) {
        modal_error_message_ = "Failed to save configuration file: " + global_config_path_;
        return false;
    }

    const bool target_changed =
        (global_config_.host != draft_settings_.host) ||
        (global_config_.port != draft_settings_.port);
    const bool ui_file_changed =
        (global_config_.ui_config_file != draft_settings_.ui_config_file);

    global_config_ = draft_settings_;

    if (ui_file_changed) {
        UIConfig loaded_ui;
        if (ConfigSerializer::LoadUIConfig(global_config_.ui_config_file, loaded_ui)) {
            ui_config_ = loaded_ui;
        }
    }

    if (target_changed) {
        state_store_.ClearState();
        client_.UpdateTarget(global_config_.host, global_config_.port);
    }

    if (callbacks_.on_save_settings) {
        callbacks_.on_save_settings(global_config_);
    }

    modal_error_message_.clear();
    show_settings_modal_ = false;
    pending_open_settings_modal_ = false;
    return true;
}

void MainControlWindow::CancelSettingsDialog() {
    modal_error_message_.clear();
    show_settings_modal_ = false;
    pending_open_settings_modal_ = false;
}

void MainControlWindow::OpenAboutDialog() {
    show_about_modal_ = true;
    pending_open_about_modal_ = true;
}

void MainControlWindow::CloseAboutDialog() {
    show_about_modal_ = false;
    pending_open_about_modal_ = false;
}

std::string MainControlWindow::BrowseYamlFileDialog(const char* dialog_title) {
#if defined(_WIN32)
    char file_buf[MAX_PATH] = {0};
    char current_dir[MAX_PATH] = {0};
    GetCurrentDirectoryA(MAX_PATH, current_dir);

    OPENFILENAMEA ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = nullptr;
    ofn.lpstrFile = file_buf;
    ofn.nMaxFile = sizeof(file_buf);
    ofn.lpstrFilter = "YAML Configuration (*.yaml;*.yml)\0*.yaml;*.yml\0All Files (*.*)\0*.*\0";
    ofn.nFilterIndex = 1;
    ofn.lpstrTitle = dialog_title;
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;

    const BOOL ok = GetOpenFileNameA(&ofn);
    SetCurrentDirectoryA(current_dir);
    if (ok) {
        return std::string(file_buf);
    }
#else
    (void)dialog_title;
#endif
    return "";
}

void MainControlWindow::RenderImGui() {
    RenderMenuBar();

    const ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);

    constexpr ImGuiWindowFlags kWindowFlags =
        ImGuiWindowFlags_NoDecoration |
        ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings;

    if (ImGui::Begin("LF Live Renderer Control", nullptr, kWindowFlags)) {
        ImGui::Spacing();
        RenderStatusSection();
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();
        RenderMainButtons();
        RenderModals();
    }
    ImGui::End();
}

void MainControlWindow::RenderMenuBar() {
    if (ImGui::BeginMainMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("Open configuration")) {
                OpenConfigurationDialog();
            }
            if (ImGui::MenuItem("Settings")) {
                OpenSettingsDialog();
            }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("Help")) {
            if (ImGui::MenuItem("About")) {
                OpenAboutDialog();
            }
            ImGui::EndMenu();
        }
        ImGui::EndMainMenuBar();
    }
}

void MainControlWindow::RenderStatusSection() {
    const auto color = GetConnectionStatusColor();
    const std::string status_text = GetConnectionStatusText();

    ImGui::TextUnformatted("Connection Status:");
    ImGui::SameLine();

    // Draw colored status indicator circle
    ImDrawList* draw_list = ImGui::GetWindowDrawList();
    const ImVec2 pos = ImGui::GetCursorScreenPos();
    const float radius = ImGui::GetTextLineHeight() * 0.40f;
    const ImVec2 center(pos.x + radius + 2.0f, pos.y + ImGui::GetTextLineHeight() * 0.50f);
    draw_list->AddCircleFilled(
        center,
        radius,
        ImGui::ColorConvertFloat4ToU32(ImVec4(color[0], color[1], color[2], color[3])));
    ImGui::Dummy(ImVec2(radius * 2.5f, ImGui::GetTextLineHeight()));
    ImGui::SameLine();

    ImGui::TextColored(ImVec4(color[0], color[1], color[2], color[3]), "%s", status_text.c_str());
}

void MainControlWindow::RenderMainButtons() {
    const float button_width = ImGui::GetContentRegionAvail().x;
    const ImVec2 button_size(button_width, 36.0f);

    if (ImGui::Button("Reconnect", button_size)) {
        ClickReconnect();
    }
    ImGui::Spacing();

    if (ImGui::Button("UI Editor", button_size)) {
        ClickUIEditor();
    }
    ImGui::Spacing();

    if (ImGui::Button("Quit", button_size)) {
        ClickQuit();
    }
}

void MainControlWindow::RenderModals() {
    // Quit Confirmation Modal
    if (pending_open_quit_modal_) {
        ImGui::OpenPopup("Confirm Quit");
        pending_open_quit_modal_ = false;
    }
    if (ImGui::BeginPopupModal("Confirm Quit", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::TextUnformatted("Are you sure you want to quit LF Live Renderer?");
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Quit", ImVec2(120.0f, 0.0f))) {
            ConfirmQuit();
            ImGui::CloseCurrentPopup();
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelQuit();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    // Open Configuration Modal
    if (pending_open_config_modal_) {
        ImGui::OpenPopup("Open Configuration");
        pending_open_config_modal_ = false;
    }
    if (ImGui::BeginPopupModal("Open Configuration", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::TextUnformatted("Global Configuration YAML File:");
        ImGui::SetNextItemWidth(280.0f);
        ImGui::InputText("##open_config_path", open_config_path_buf_, sizeof(open_config_path_buf_));
        ImGui::SameLine();
        if (ImGui::Button("Browse...")) {
            std::string picked = BrowseYamlFileDialog("Open Global Configuration File");
            if (!picked.empty()) {
                std::snprintf(open_config_path_buf_, sizeof(open_config_path_buf_), "%s", picked.c_str());
            }
        }

        if (!modal_error_message_.empty()) {
            ImGui::Spacing();
            ImGui::TextColored(ImVec4(0.95f, 0.30f, 0.25f, 1.0f), "%s", modal_error_message_.c_str());
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Open", ImVec2(120.0f, 0.0f))) {
            if (ConfirmOpenConfiguration(open_config_path_buf_)) {
                ImGui::CloseCurrentPopup();
            }
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelOpenConfiguration();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    // Settings Modal
    if (pending_open_settings_modal_) {
        ImGui::OpenPopup("Settings");
        pending_open_settings_modal_ = false;
    }
    if (ImGui::BeginPopupModal("Settings", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::SetNextItemWidth(260.0f);
        ImGui::InputText("Server IP / Host", settings_host_buf_, sizeof(settings_host_buf_));

        ImGui::SetNextItemWidth(260.0f);
        ImGui::InputInt("Consumer Port", &settings_port_);

        ImGui::SetNextItemWidth(260.0f);
        ImGui::InputText("UI Configuration File", settings_ui_file_buf_, sizeof(settings_ui_file_buf_));
        ImGui::SameLine();
        if (ImGui::Button("Browse...##browse_ui")) {
            std::string picked = BrowseYamlFileDialog("Select UI Configuration File");
            if (!picked.empty()) {
                std::snprintf(settings_ui_file_buf_, sizeof(settings_ui_file_buf_), "%s", picked.c_str());
            }
        }

        if (!modal_error_message_.empty()) {
            ImGui::Spacing();
            ImGui::TextColored(ImVec4(0.95f, 0.30f, 0.25f, 1.0f), "%s", modal_error_message_.c_str());
        }

        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("Save", ImVec2(120.0f, 0.0f))) {
            if (SaveSettingsDialog()) {
                ImGui::CloseCurrentPopup();
            }
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel", ImVec2(120.0f, 0.0f))) {
            CancelSettingsDialog();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }

    // About Modal
    if (pending_open_about_modal_) {
        ImGui::OpenPopup("About");
        pending_open_about_modal_ = false;
    }
    if (ImGui::BeginPopupModal("About", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::Text("Application: %s", kAppName);
        ImGui::Text("Version: %s", kLiveRendererVersion);
        ImGui::Text("Author: %s", kAppAuthor);
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();

        if (ImGui::Button("OK", ImVec2(120.0f, 0.0f))) {
            CloseAboutDialog();
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }
}

}  // namespace live_renderer
