#ifndef LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_

#include <array>
#include <functional>
#include <string>
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"

namespace live_renderer {

/**
 * @brief Main control window managing connection status, primary control buttons,
 *        menus (File -> Open configuration / Settings, Help -> About), and modal dialogs.
 */
class MainControlWindow {
public:
    struct Callbacks {
        std::function<void()> on_reconnect;
        std::function<void()> on_enter_ui_editor;
        std::function<void(const std::string& config_path)> on_open_configuration;
        std::function<void(const GlobalConfig& new_config)> on_save_settings;
    };

    MainControlWindow(
        const std::string& global_config_path,
        GlobalConfig& global_config,
        UIConfig& ui_config,
        LiveStateStore& state_store,
        TcpConsumerClient& client);

    ~MainControlWindow() = default;

    void SetCallbacks(Callbacks callbacks);

    /**
     * @brief Renders the Main Control Window contents using Dear ImGui.
     *        Must be called within an active ImGui frame.
     */
    void RenderImGui();

    // Status helpers
    ConnectionStatus GetConnectionStatus() const;
    std::string GetConnectionStatusText() const;
    std::array<float, 4> GetConnectionStatusColor() const;

    // Button & menu actions (callable directly in unit tests or via ImGui buttons)
    void ClickReconnect();
    void ClickUIEditor();
    void ClickQuit();
    void ConfirmQuit();
    void CancelQuit();

    void OpenConfigurationDialog();
    bool ConfirmOpenConfiguration(const std::string& new_config_path);
    void CancelOpenConfiguration();

    void OpenSettingsDialog();
    bool SaveSettingsDialog();
    void CancelSettingsDialog();

    void OpenAboutDialog();
    void CloseAboutDialog();

    // State inspection
    bool IsQuitConfirmationOpen() const { return show_quit_confirm_modal_; }
    bool IsQuitConfirmed() const { return quit_confirmed_; }
    bool IsInUIEditorMode() const { return in_ui_editor_mode_; }
    void SetUIEditorMode(bool enabled) { in_ui_editor_mode_ = enabled; }

    bool IsOpenConfigDialogOpen() const { return show_open_config_modal_; }
    bool IsSettingsDialogOpen() const { return show_settings_modal_; }
    bool IsAboutDialogOpen() const { return show_about_modal_; }
    const std::string& GetModalErrorMessage() const { return modal_error_message_; }

    // About metadata
    static const char* GetApplicationName();
    static const char* GetApplicationVersion();
    static const char* GetApplicationAuthor();

    // Draft settings accessors for Settings dialog & tests
    void SetDraftSettings(const std::string& host, int port, const std::string& ui_config_file);
    const GlobalConfig& GetDraftSettings() const { return draft_settings_; }
    const std::string& GetGlobalConfigPath() const { return global_config_path_; }

private:
    void RenderMenuBar();
    void RenderStatusSection();
    void RenderMainButtons();
    void RenderModals();
    static std::string BrowseYamlFileDialog(const char* dialog_title);

    std::string global_config_path_;
    GlobalConfig& global_config_;
    UIConfig& ui_config_;
    LiveStateStore& state_store_;
    TcpConsumerClient& client_;
    Callbacks callbacks_;

    bool in_ui_editor_mode_ = false;

    bool show_quit_confirm_modal_ = false;
    bool pending_open_quit_modal_ = false;
    bool quit_confirmed_ = false;

    bool show_open_config_modal_ = false;
    bool pending_open_config_modal_ = false;
    char open_config_path_buf_[512]{};

    bool show_settings_modal_ = false;
    bool pending_open_settings_modal_ = false;
    GlobalConfig draft_settings_;
    char settings_host_buf_[256]{};
    int settings_port_ = 8001;
    char settings_ui_file_buf_[512]{};

    bool show_about_modal_ = false;
    bool pending_open_about_modal_ = false;

    std::string modal_error_message_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_
