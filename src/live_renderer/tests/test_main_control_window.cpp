#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/version.hpp"
#include "live_renderer/windows/main_control_window.hpp"

using namespace live_renderer;

TEST(MainControlWindowTest, DisplaysInitialConnectionStatus) {
    GlobalConfig global_cfg{"127.0.0.1", 8001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);

    EXPECT_EQ(win.GetConnectionStatus(), ConnectionStatus::Disconnected);
    EXPECT_EQ(win.GetConnectionStatusText(), "Disconnected (127.0.0.1:8001)");
    auto color = win.GetConnectionStatusColor();
    EXPECT_GT(color[0], 0.8f);  // Red channel dominant when disconnected
}

TEST(MainControlWindowTest, ReconnectResetsStateAndTriggersCallback) {
    GlobalConfig global_cfg{"127.0.0.1", 8001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    // Populate state store with a player
    store.ResetSession();
    store.UpdatePlayerDescription(11, "Alpha", "#101", 1, "commander");
    ASSERT_FALSE(store.GetSnapshot().players.empty());
    ASSERT_TRUE(store.GetSnapshot().in_session);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);
    bool reconnect_called = false;
    MainControlWindow::Callbacks cbs;
    cbs.on_reconnect = [&]() { reconnect_called = true; };
    win.SetCallbacks(cbs);

    win.ClickReconnect();
    EXPECT_TRUE(reconnect_called);
    EXPECT_TRUE(store.GetSnapshot().players.empty());
    EXPECT_FALSE(store.GetSnapshot().in_session);
}

TEST(MainControlWindowTest, UIEditorButtonEntersEditorMode) {
    GlobalConfig global_cfg;
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);
    bool editor_entered = false;
    MainControlWindow::Callbacks cbs;
    cbs.on_enter_ui_editor = [&]() { editor_entered = true; };
    win.SetCallbacks(cbs);

    EXPECT_FALSE(win.IsInUIEditorMode());
    win.ClickUIEditor();
    EXPECT_TRUE(win.IsInUIEditorMode());
    EXPECT_TRUE(editor_entered);
}

TEST(MainControlWindowTest, QuitButtonRequiresConfirmation) {
    GlobalConfig global_cfg;
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);

    EXPECT_FALSE(win.IsQuitConfirmationOpen());
    EXPECT_FALSE(win.IsQuitConfirmed());

    win.ClickQuit();
    EXPECT_TRUE(win.IsQuitConfirmationOpen());
    EXPECT_FALSE(win.IsQuitConfirmed());

    win.CancelQuit();
    EXPECT_FALSE(win.IsQuitConfirmationOpen());
    EXPECT_FALSE(win.IsQuitConfirmed());

    win.ClickQuit();
    win.ConfirmQuit();
    EXPECT_FALSE(win.IsQuitConfirmationOpen());
    EXPECT_TRUE(win.IsQuitConfirmed());
}

TEST(MainControlWindowTest, SettingsModalSavesCancelAndValidates) {
    const std::string cfg_path = "test_settings_modal.yaml";
    GlobalConfig global_cfg{"127.0.0.1", 8001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win(cfg_path, global_cfg, ui_cfg, store, client);

    // Test Cancel leaves config untouched
    win.OpenSettingsDialog();
    EXPECT_TRUE(win.IsSettingsDialogOpen());
    win.SetDraftSettings("192.168.1.99", 8000, "ignored.yaml");
    win.CancelSettingsDialog();
    EXPECT_FALSE(win.IsSettingsDialogOpen());
    EXPECT_EQ(global_cfg.host, "127.0.0.1");
    EXPECT_EQ(global_cfg.port, 8001);

    // Test validation failure on invalid port
    win.OpenSettingsDialog();
    win.SetDraftSettings("10.0.0.42", 0, "arena_ui.yaml");
    EXPECT_FALSE(win.SaveSettingsDialog());
    EXPECT_TRUE(win.IsSettingsDialogOpen());
    EXPECT_FALSE(win.GetModalErrorMessage().empty());

    // Test valid Save
    win.SetDraftSettings("10.0.0.42", 9555, "arena_ui.yaml");
    EXPECT_TRUE(win.SaveSettingsDialog());
    EXPECT_FALSE(win.IsSettingsDialogOpen());
    EXPECT_TRUE(win.GetModalErrorMessage().empty());

    EXPECT_EQ(global_cfg.host, "10.0.0.42");
    EXPECT_EQ(global_cfg.port, 9555);
    EXPECT_EQ(global_cfg.ui_config_file, "arena_ui.yaml");
    EXPECT_EQ(client.GetHost(), "10.0.0.42");
    EXPECT_EQ(client.GetPort(), 9555);

    GlobalConfig disk_cfg;
    EXPECT_TRUE(ConfigSerializer::LoadGlobalConfig(cfg_path, disk_cfg));
    EXPECT_EQ(disk_cfg.host, "10.0.0.42");
    EXPECT_EQ(disk_cfg.port, 9555);

    std::filesystem::remove(cfg_path);
}

TEST(MainControlWindowTest, OpenConfigurationResetsProgramStateAndLoadsUI) {
    const std::string new_cfg_path = "test_open_new_cfg.yaml";
    const std::string new_ui_path = "test_open_new_ui.yaml";

    UIConfig saved_ui;
    WindowConfig wcfg;
    wcfg.id = 1;
    wcfg.title = "Custom Scoreboard Window";
    saved_ui.windows.push_back(wcfg);
    ASSERT_TRUE(ConfigSerializer::SaveUIConfig(new_ui_path, saved_ui));

    GlobalConfig saved_cfg{"192.168.10.20", 9123, new_ui_path};
    ASSERT_TRUE(ConfigSerializer::SaveGlobalConfig(new_cfg_path, saved_cfg));

    GlobalConfig global_cfg{"127.0.0.1", 8001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    store.ResetSession();
    store.UpdatePlayerDescription(11, "Alpha", "#101", 1, "commander");

    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("initial.yaml", global_cfg, ui_cfg, store, client);
    win.ClickUIEditor();
    EXPECT_TRUE(win.IsInUIEditorMode());

    win.OpenConfigurationDialog();
    EXPECT_TRUE(win.IsOpenConfigDialogOpen());

    // Invalid file path should fail and stay open
    EXPECT_FALSE(win.ConfirmOpenConfiguration("non_existent_config_12345.yaml"));
    EXPECT_TRUE(win.IsOpenConfigDialogOpen());
    EXPECT_FALSE(win.GetModalErrorMessage().empty());

    // Valid file path resets state and loads new config + UI config
    EXPECT_TRUE(win.ConfirmOpenConfiguration(new_cfg_path));
    EXPECT_FALSE(win.IsOpenConfigDialogOpen());
    EXPECT_FALSE(win.IsInUIEditorMode());
    EXPECT_EQ(global_cfg.host, "192.168.10.20");
    EXPECT_EQ(global_cfg.port, 9123);
    EXPECT_EQ(client.GetHost(), "192.168.10.20");
    EXPECT_EQ(client.GetPort(), 9123);
    EXPECT_TRUE(store.GetSnapshot().players.empty());
    EXPECT_FALSE(store.GetSnapshot().in_session);
    ASSERT_EQ(ui_cfg.windows.size(), 1u);
    EXPECT_EQ(ui_cfg.windows[0].title, "Custom Scoreboard Window");

    std::filesystem::remove(new_cfg_path);
    std::filesystem::remove(new_ui_path);
}

TEST(MainControlWindowTest, AboutModalAndMetadata) {
    GlobalConfig global_cfg;
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);
    EXPECT_FALSE(win.IsAboutDialogOpen());

    win.OpenAboutDialog();
    EXPECT_TRUE(win.IsAboutDialogOpen());
    EXPECT_STREQ(MainControlWindow::GetApplicationName(), "LF Live Renderer");
    EXPECT_STREQ(MainControlWindow::GetApplicationVersion(), kLiveRendererVersion);
    EXPECT_STREQ(MainControlWindow::GetApplicationVersion(), "0.1.5");
    EXPECT_STREQ(MainControlWindow::GetApplicationAuthor(), "EboMike");

    win.CloseAboutDialog();
    EXPECT_FALSE(win.IsAboutDialogOpen());
}
