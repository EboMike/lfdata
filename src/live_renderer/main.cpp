#include "live_renderer/config/global_config.hpp"
#include "live_renderer/config/ui_config.hpp"
#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/state/mock_game_state.hpp"
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include <iostream>
#include <csignal>
#include <atomic>
#include <thread>
#include <chrono>

namespace {
std::atomic<bool> g_shutdown_requested{false};

void SignalHandler(int) {
    g_shutdown_requested.store(true);
}
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, SignalHandler);
    std::signal(SIGTERM, SignalHandler);

    std::string config_path = "live_renderer_config.yaml";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) {
            config_path = argv[++i];
        }
    }

    live_renderer::GlobalConfig global_cfg;
    if (!live_renderer::ConfigSerializer::LoadGlobalConfig(config_path, global_cfg)) {
        std::cout << "[live_renderer] Warning: Could not load " << config_path << ", generating default config.\n";
        live_renderer::ConfigSerializer::SaveGlobalConfig(config_path, global_cfg);
    }

    live_renderer::UIConfig ui_cfg;
    if (!live_renderer::ConfigSerializer::LoadUIConfig(global_cfg.ui_config_file, ui_cfg)) {
        std::cout << "[live_renderer] Warning: Could not load " << global_cfg.ui_config_file << ", creating default UI layout.\n";
        live_renderer::ConfigSerializer::SaveUIConfig(global_cfg.ui_config_file, ui_cfg);
    }

    live_renderer::LiveStateStore state_store;
    live_renderer::ProtocolParser parser(state_store);
    live_renderer::TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    std::cout << "[live_renderer] Connecting to lflive at " << global_cfg.host << ":" << global_cfg.port << "...\n";
    client.Start();

    while (!g_shutdown_requested.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    std::cout << "[live_renderer] Shutting down...\n";
    client.Stop();
    return 0;
}

