#ifndef LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_

#include <array>
#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/lfstats/competition_info.hpp"
#include "live_renderer/lfstats/lfstats_fetcher.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"

namespace live_renderer {

/**
 * @brief Dynamic loading states for competition dropdown element.
 */
enum class CompetitionLoadingState {
    kLoading,
    kLoaded,
    kError
};

/**
 * @brief Main control window managing connection status, primary control buttons,
 *        competition dropdown, menus (File -> Open configuration / Settings,
 *        Help -> About), and modal dialogs.
 */
class MainControlWindow {
public:
    struct Callbacks {
        std::function<void()> on_reconnect;
        std::function<void()> on_enter_ui_editor;
        std::function<void(const std::string& config_path)> on_open_configuration;
        std::function<void(const GlobalConfig& new_config)> on_save_settings;
        std::function<void(const CompetitionInfo& competition)> on_competition_selected;
        std::function<void(const std::vector<ScheduledGame>& schedule)> on_schedule_loaded;
    };

    MainControlWindow(
        const std::string& global_config_path,
        GlobalConfig& global_config,
        UIConfig& ui_config,
        LiveStateStore& state_store,
        TcpConsumerClient& client,
        std::shared_ptr<LFStatsFetcher> stats_fetcher = nullptr);

    ~MainControlWindow();

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

    // Competition management & dropdown helpers
    void SetStatsFetcher(
        std::shared_ptr<LFStatsFetcher> fetcher,
        bool auto_fetch = true);
    void StartFetchCompetitions();
    bool WaitForCompetitionFetch(int timeout_ms = 2000);

    CompetitionLoadingState GetCompetitionLoadingState() const;
    std::string GetCompetitionDropdownText() const;
    std::vector<CompetitionInfo> GetCompetitions() const;
    const CompetitionInfo* GetSelectedCompetition() const;
    int GetSelectedCompetitionIndex() const;
    std::string GetSelectedCompetitionSlug() const;
    std::string GetCompetitionErrorMessage() const;

    void SelectCompetition(int index);
    bool SelectCompetitionBySlug(const std::string& slug);
    void LoadCompetitionDetails(const std::string& slug);
    bool WaitForCompetitionDetails(int timeout_ms = 2000);

    // Schedule access & fetch
    void FetchTournamentSchedule(const std::string& tournament_slug);
    std::vector<ScheduledGame> GetSchedule() const;
    bool HasSchedule() const;
    bool WaitForSchedule(int timeout_ms = 2000);

    // Mock/Testing helpers
    void SetCompetitionsForTesting(const std::vector<CompetitionInfo>& competitions);
    void SetCompetitionErrorForTesting(const std::string& error_message);
    void SetCompetitionLoadingForTesting();

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
    void SetDraftSettings(
        const std::string& host,
        int port,
        const std::string& ui_config_file,
        const std::string& default_profile_picture_url = "");
    const GlobalConfig& GetDraftSettings() const { return draft_settings_; }
    const std::string& GetGlobalConfigPath() const { return global_config_path_; }

private:
    void RenderMenuBar();
    void RenderStatusSection();
    void RenderCompetitionSection();
    void RenderMainButtons();
    void RenderModals();
    static std::string BrowseYamlFileDialog(const char* dialog_title);

    std::string GetCompetitionDropdownTextLocked() const;

    std::string global_config_path_;
    GlobalConfig& global_config_;
    UIConfig& ui_config_;
    LiveStateStore& state_store_;
    TcpConsumerClient& client_;
    Callbacks callbacks_;

    std::shared_ptr<LFStatsFetcher> stats_fetcher_;
    std::shared_ptr<std::atomic<bool>> is_alive_;
    mutable std::mutex competitions_mutex_;
    CompetitionLoadingState competition_state_{CompetitionLoadingState::kLoading};
    std::vector<CompetitionInfo> competitions_;
    int selected_competition_index_{-1};
    std::string competition_error_message_;

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
    char settings_default_picture_url_buf_[512]{};
    std::atomic<bool> details_loading_{false};

    mutable std::mutex schedule_mutex_;
    std::vector<ScheduledGame> schedule_;
    std::atomic<bool> schedule_loading_{false};

    bool show_about_modal_ = false;
    bool pending_open_about_modal_ = false;

    std::string modal_error_message_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_MAIN_CONTROL_WINDOW_HPP_
