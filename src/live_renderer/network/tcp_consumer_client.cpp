#include "live_renderer/network/tcp_consumer_client.hpp"
#include <chrono>
#include <vector>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
using socket_t = SOCKET;
#define INVALID_SOCK INVALID_SOCKET
#define CLOSE_SOCK closesocket
#else
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <fcntl.h>
using socket_t = int;
#define INVALID_SOCK (-1)
#define CLOSE_SOCK close
#endif

namespace live_renderer {

TcpConsumerClient::TcpConsumerClient(ProtocolParser& parser, std::string host, int port)
    : parser_(parser), host_(std::move(host)), port_(port) {
#if defined(_WIN32)
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
}

TcpConsumerClient::~TcpConsumerClient() {
    Stop();
#if defined(_WIN32)
    WSACleanup();
#endif
}

void TcpConsumerClient::Start() {
    if (running_.load()) return;
    running_.store(true);
    thread_ = std::thread(&TcpConsumerClient::WorkerLoop, this);
}

void TcpConsumerClient::Stop() {
    running_.store(false);
    if (thread_.joinable()) {
        thread_.join();
    }
}

void TcpConsumerClient::Reconnect() {
    reconnect_requested_.store(true);
}

void TcpConsumerClient::UpdateTarget(const std::string& host, int port) {
    host_ = host;
    port_ = port;
    reconnect_requested_.store(true);
}

std::string TcpConsumerClient::GetHost() const {
    return host_;
}

int TcpConsumerClient::GetPort() const {
    return port_;
}

void TcpConsumerClient::CloseSocket(uintptr_t& sock) {
    if (static_cast<socket_t>(sock) != INVALID_SOCK) {
        CLOSE_SOCK(static_cast<socket_t>(sock));
        sock = static_cast<uintptr_t>(INVALID_SOCK);
    }
}

bool TcpConsumerClient::TryConnectSocket(uintptr_t& out_sock) {
    socket_t s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCK) return false;

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<uint16_t>(port_));
    inet_pton(AF_INET, host_.c_str(), &addr.sin_addr);

    // Set non-blocking during connect check
#if defined(_WIN32)
    u_long mode = 1;
    ioctlsocket(s, FIONBIO, &mode);
#else
    int flags = fcntl(s, F_GETFL, 0);
    fcntl(s, F_SETFL, flags | O_NONBLOCK);
#endif

    int res = connect(s, reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
    if (res < 0) {
#if defined(_WIN32)
        int err = WSAGetLastError();
        if (err != WSAEWOULDBLOCK) {
            CLOSE_SOCK(s);
            return false;
        }
#else
        if (errno != EINPROGRESS) {
            CLOSE_SOCK(s);
            return false;
        }
#endif
        fd_set wfds;
        FD_ZERO(&wfds);
        FD_SET(s, &wfds);
        timeval tv{1, 0}; // 1 sec timeout
        int sel = select(static_cast<int>(s + 1), nullptr, &wfds, nullptr, &tv);
        if (sel <= 0) {
            CLOSE_SOCK(s);
            return false;
        }
    }

    out_sock = static_cast<uintptr_t>(s);
    return true;
}

void TcpConsumerClient::WorkerLoop() {
    uintptr_t sock = static_cast<uintptr_t>(INVALID_SOCK);
    std::string line_buffer;
    std::vector<char> recv_buf(4096);

    while (running_.load()) {
        if (reconnect_requested_.load()) {
            reconnect_requested_.store(false);
            CloseSocket(sock);
            status_.store(ConnectionStatus::Disconnected);
        }

        if (static_cast<socket_t>(sock) == INVALID_SOCK) {
            status_.store(ConnectionStatus::Connecting);
            if (!TryConnectSocket(sock)) {
                status_.store(ConnectionStatus::Disconnected);
                // Sleep with interruption check
                for (int i = 0; i < 20 && running_.load() && !reconnect_requested_.load(); ++i) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                }
                continue;
            }
            status_.store(ConnectionStatus::Connected);
            line_buffer.clear();
        }

        // Poll socket for read
        fd_set rfds;
        FD_ZERO(&rfds);
        FD_SET(static_cast<socket_t>(sock), &rfds);
        timeval tv{0, 100000}; // 100ms
        int sel = select(static_cast<int>(sock + 1), &rfds, nullptr, nullptr, &tv);

        if (sel < 0) {
            CloseSocket(sock);
            status_.store(ConnectionStatus::Disconnected);
            continue;
        }

        if (sel > 0 && FD_ISSET(static_cast<socket_t>(sock), &rfds)) {
            int n = recv(static_cast<socket_t>(sock), recv_buf.data(), static_cast<int>(recv_buf.size()), 0);
            if (n <= 0) {
                // Connection closed or error
                CloseSocket(sock);
                status_.store(ConnectionStatus::Disconnected);
                continue;
            }

            line_buffer.append(recv_buf.data(), n);

            // Extract lines separated by \r\n or \n
            size_t pos = 0;
            while ((pos = line_buffer.find('\n')) != std::string::npos) {
                std::string line = line_buffer.substr(0, pos);
                line_buffer.erase(0, pos + 1);
                parser_.ParseLine(line);
            }
        }
    }

    CloseSocket(sock);
    status_.store(ConnectionStatus::Disconnected);
}

}  // namespace live_renderer

