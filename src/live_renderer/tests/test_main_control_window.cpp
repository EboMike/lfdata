#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/windows/main_control_window.hpp"

using namespace live_renderer;

TEST(MainControlWindowTest, DisplaysInitialConnectionStatus) {
    GlobalConfig global_cfg{"127.0.0.1", 9001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);

    EXPECT_EQ(win.GetConnectionStatus(), ConnectionStatus::Disconnected);
    EXPECT_EQ(win.GetConnectionStatusText(), "Disconnected (127.0.0.1:9001)");
    auto color = win.GetConnectionStatusColor();
    EXPECT_GT(color[0], 0.8f);  // Red channel dominant when disconnected
}

TEST(MainControlWindowTest, ReconnectResetsStateAndTriggersCallback) {
    GlobalConfig global_cfg{"127.0.0.1", 9001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    // Populate state store with a player
    store.UpdatePlayerDescription(11, "Alpha", "#101", 1, "commander");
    ASSERT_FALSE(store.GetSnapshot().players.empty());

    MainControlWindow win("test_ctrl_cfg.yaml", global_cfg, ui_cfg, store, client);
    bool reconnect_called = false;
    MainControlWindow::Callbacks cbs;
    cbs.on_reconnect = [&]() { reconnect_called = true; };
    win.SetCallbacks(cbs);

    win.ClickReconnect();
    EXPECT_TRUE(reconnect_called);
    EXPECT_TRUE(store.GetSnapshot().players.empty());
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

TEST(MainControlWindowTest, SettingsModalSavesAndUpdatesTarget) {
    const std::string cfg_path = "test_settings_modal.yaml";
    GlobalConfig global_cfg{"127.0.0.1", 9001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win(cfg_path, global_cfg, ui_cfg, store, client);
    win.OpenSettingsDialog();
    EXPECT_TRUE(win.IsSettingsDialogOpen());

    win.SetDraftSettings("10.0.0.42", 9555, "arena_ui.yaml");
    EXPECT_TRUE(win.SaveSettingsDialog());
    EXPECT_FALSE(win.IsSettingsDialogOpen());

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

TEST(MainControlWindowTest, OpenConfigurationResetsProgramState) {
    const std::string new_cfg_path = "test_open_new_cfg.yaml";
    GlobalConfig saved_cfg{"192.168.10.20", 9123, "custom_ui.yaml"};
    ASSERT_TRUE(ConfigSerializer::SaveGlobalConfig(new_cfg_path, saved_cfg));

    GlobalConfig global_cfg{"127.0.0.1", 9001, "ui_layout.yaml"};
    UIConfig ui_cfg;
    LiveStateStore store;
    store.UpdatePlayerDescription(11, "Alpha", "#101", 1, "commander");

    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("initial.yaml", global_cfg, ui_cfg, store, client);
    win.OpenConfigurationDialog();
    EXPECT_TRUE(win.IsOpenConfigDialogOpen());

    EXPECT_TRUE(win.ConfirmOpenConfiguration(new_cfg_path));
    EXPECT_FALSE(win.IsOpenConfigDialogOpen());
    EXPECT_EQ(global_cfg.host, "192.168.10.20");
    EXPECT_EQ(global_cfg.port, 9123);
    EXPECT_EQ(client.GetHost(), "192.168.10.20");
    EXPECT_EQ(client.GetPort(), 9123);
    EXPECT_TRUE(store.GetSnapshot().players.empty());

    std::filesystem::remove(new_cfg_path);
}

