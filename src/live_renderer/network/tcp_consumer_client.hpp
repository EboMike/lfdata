#ifndef LIVE_RENDERER_NETWORK_TCP_CONSUMER_CLIENT_HPP_
#define LIVE_RENDERER_NETWORK_TCP_CONSUMER_CLIENT_HPP_

#include <string>
#include <thread>
#include <atomic>
#include "live_renderer/network/protocol_parser.hpp"

namespace live_renderer {

enum class ConnectionStatus {
    Disconnected,
    Connecting,
    Connected
};

/**
 * @brief Non-blocking background TCP socket consumer thread that connects to lflive.
 */
class TcpConsumerClient {
public:
    TcpConsumerClient(ProtocolParser& parser, std::string host, int port);
    ~TcpConsumerClient();

    void Start();
    void Stop();
    void Reconnect();
    void UpdateTarget(const std::string& host, int port);

    ConnectionStatus GetStatus() const { return status_.load(); }
    std::string GetHost() const;
    int GetPort() const;

private:
    void WorkerLoop();
    bool TryConnectSocket(uintptr_t& out_sock);
    void CloseSocket(uintptr_t& sock);

    ProtocolParser& parser_;
    std::string host_;
    int port_;
    std::atomic<ConnectionStatus> status_{ConnectionStatus::Disconnected};
    std::atomic<bool> running_{false};
    std::atomic<bool> reconnect_requested_{false};
    std::thread thread_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_NETWORK_TCP_CONSUMER_CLIENT_HPP_

