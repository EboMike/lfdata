/**
 * @file rtsp_feed_reader.cpp
 * @brief Implementation of RtspFeedReader using ffprobe and ffmpeg subprocesses.
 */

#include "live_renderer/feeds/rtsp_feed_reader.hpp"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <sstream>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace live_renderer {

namespace {

constexpr int kMaxPreviewWidth = 640;
constexpr int kProbeTimeoutMs = 5000;

std::string ToLowerAscii(std::string s) {
    for (char& ch : s) {
        ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    }
    return s;
}

std::string TrimAscii(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) {
        ++start;
    }
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(start, end - start);
}

std::string QuoteArg(const std::string& arg) {
    std::string out = "\"";
    for (char c : arg) {
        if (c == '"') {
            out += "\\\"";
        } else {
            out += c;
        }
    }
    out += '"';
    return out;
}

#if defined(_WIN32)
bool ProbeRtspDimensions(
    const std::string& url,
    int& out_width,
    int& out_height,
    std::string& out_error,
    const std::atomic<bool>& stop_requested) {
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;

    HANDLE read_pipe = nullptr;
    HANDLE write_pipe = nullptr;
    if (!CreatePipe(&read_pipe, &write_pipe, &sa, 0)) {
        out_error = "Failed to create pipe for ffprobe.";
        return false;
    }
    SetHandleInformation(read_pipe, HANDLE_FLAG_INHERIT, 0);

    std::string cmd =
        "ffprobe -v error -rtsp_transport tcp -rw_timeout 5000000 "
        "-select_streams v:0 -show_entries stream=width,height "
        "-of csv=p=0:s=x " + QuoteArg(url);

    STARTUPINFOA si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = write_pipe;
    si.hStdError = write_pipe;

    PROCESS_INFORMATION pi{};
    std::vector<char> cmd_buf(cmd.begin(), cmd.end());
    cmd_buf.push_back('\0');

    BOOL created = CreateProcessA(
        nullptr,
        cmd_buf.data(),
        nullptr,
        nullptr,
        TRUE,
        CREATE_NO_WINDOW,
        nullptr,
        nullptr,
        &si,
        &pi);
    CloseHandle(write_pipe);

    if (!created) {
        CloseHandle(read_pipe);
        out_error = "Failed to launch ffprobe. Ensure FFmpeg is installed on PATH.";
        return false;
    }

    std::string output;
    char buf[512];
    DWORD bytes_read = 0;
    DWORD elapsed_ms = 0;
    while (!stop_requested.load()) {
        DWORD avail = 0;
        if (PeekNamedPipe(read_pipe, nullptr, 0, nullptr, &avail, nullptr) && avail > 0) {
            if (ReadFile(read_pipe, buf, sizeof(buf) - 1, &bytes_read, nullptr) && bytes_read > 0) {
                buf[bytes_read] = '\0';
                output += buf;
            }
        } else {
            DWORD wait_rc = WaitForSingleObject(pi.hProcess, 50);
            elapsed_ms += 50;
            if (wait_rc == WAIT_OBJECT_0) {
                while (ReadFile(read_pipe, buf, sizeof(buf) - 1, &bytes_read, nullptr) &&
                       bytes_read > 0) {
                    buf[bytes_read] = '\0';
                    output += buf;
                }
                break;
            }
            if (elapsed_ms >= static_cast<DWORD>(kProbeTimeoutMs)) {
                TerminateProcess(pi.hProcess, 1);
                CloseHandle(pi.hThread);
                CloseHandle(pi.hProcess);
                CloseHandle(read_pipe);
                out_error = "Timed out connecting to RTSP stream.";
                return false;
            }
        }
    }

    if (stop_requested.load()) {
        TerminateProcess(pi.hProcess, 1);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        CloseHandle(read_pipe);
        out_error = "Connection cancelled.";
        return false;
    }

    DWORD exit_code = 1;
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    CloseHandle(read_pipe);

    if (exit_code != 0) {
        std::string trimmed = TrimAscii(output);
        out_error = trimmed.empty()
            ? "Unable to connect to RTSP stream."
            : trimmed;
        return false;
    }

    std::string trimmed = TrimAscii(output);
    size_t x_pos = trimmed.find('x');
    if (x_pos == std::string::npos) {
        out_error = "Could not determine video stream dimensions.";
        return false;
    }

    int w = std::atoi(trimmed.substr(0, x_pos).c_str());
    int h = std::atoi(trimmed.substr(x_pos + 1).c_str());
    if (w <= 0 || h <= 0) {
        out_error = "Invalid video stream dimensions reported by ffprobe.";
        return false;
    }

    if (w > kMaxPreviewWidth) {
        h = std::max(2, (h * kMaxPreviewWidth / w) & ~1);
        w = kMaxPreviewWidth;
    }
    out_width = w;
    out_height = h;
    return true;
}
#endif

}  // namespace

RtspFeedReader::~RtspFeedReader() {
    Close();
}

bool RtspFeedReader::ValidateRtspUrl(const std::string& url, std::string& out_error) {
    std::string trimmed = TrimAscii(url);
    if (trimmed.empty()) {
        out_error = "RTSP URL cannot be empty.";
        return false;
    }

    for (char ch : trimmed) {
        if (std::isspace(static_cast<unsigned char>(ch))) {
            out_error = "RTSP URL cannot contain whitespace.";
            return false;
        }
    }

    const std::string lower = ToLowerAscii(trimmed);
    size_t scheme_len = 0;
    if (lower.rfind("rtsp://", 0) == 0) {
        scheme_len = 7;
    } else if (lower.rfind("rtsps://", 0) == 0) {
        scheme_len = 8;
    } else {
        out_error = "Invalid URL: must start with rtsp:// or rtsps://.";
        return false;
    }

    std::string rest = trimmed.substr(scheme_len);
    size_t slash_pos = rest.find_first_of("/?#");
    std::string authority = (slash_pos == std::string::npos)
        ? rest
        : rest.substr(0, slash_pos);

    size_t at_pos = authority.rfind('@');
    if (at_pos != std::string::npos) {
        authority = authority.substr(at_pos + 1);
    }

    if (authority.empty()) {
        out_error = "Invalid RTSP URL: missing host.";
        return false;
    }

    std::string host;
    std::string port_str;
    if (authority.front() == '[') {
        size_t close_bracket = authority.find(']');
        if (close_bracket == std::string::npos || close_bracket == 1) {
            out_error = "Invalid RTSP URL: malformed IPv6 host.";
            return false;
        }
        host = authority.substr(1, close_bracket - 1);
        if (close_bracket + 1 < authority.size()) {
            if (authority[close_bracket + 1] != ':') {
                out_error = "Invalid RTSP URL: unexpected characters after host.";
                return false;
            }
            port_str = authority.substr(close_bracket + 2);
        }
    } else {
        size_t colon_pos = authority.find(':');
        if (colon_pos != std::string::npos) {
            host = authority.substr(0, colon_pos);
            port_str = authority.substr(colon_pos + 1);
        } else {
            host = authority;
        }
    }

    if (host.empty()) {
        out_error = "Invalid RTSP URL: missing host.";
        return false;
    }

    if (!port_str.empty()) {
        for (char ch : port_str) {
            if (!std::isdigit(static_cast<unsigned char>(ch))) {
                out_error = "Invalid RTSP URL: port must be numeric.";
                return false;
            }
        }
        long port_val = std::strtol(port_str.c_str(), nullptr, 10);
        if (port_val < 1 || port_val > 65535) {
            out_error = "Invalid RTSP URL: port must be between 1 and 65535.";
            return false;
        }
    }

    out_error.clear();
    return true;
}

bool RtspFeedReader::Open(const std::string& url) {
    Close();

    std::string trimmed = TrimAscii(url);
    std::string validation_error;
    if (!ValidateRtspUrl(trimmed, validation_error)) {
        std::lock_guard<std::mutex> lock(mutex_);
        url_ = trimmed;
        state_ = FeedConnectionState::kError;
        error_message_ = validation_error;
        return false;
    }

    {
        std::lock_guard<std::mutex> lock(mutex_);
        url_ = trimmed;
        state_ = FeedConnectionState::kConnecting;
        error_message_.clear();
        width_ = 0;
        height_ = 0;
        frame_seq_ = 0;
        latest_frame_rgba_.clear();
    }

    stop_requested_.store(false);
    worker_thread_ = std::thread(&RtspFeedReader::WorkerLoop, this, trimmed);
    return true;
}

void RtspFeedReader::Close() {
    stop_requested_.store(true);
#if defined(_WIN32)
    {
        std::lock_guard<std::mutex> lock(process_mutex_);
        if (active_process_handle_) {
            TerminateProcess(static_cast<HANDLE>(active_process_handle_), 0);
        }
    }
#endif
    if (worker_thread_.joinable()) {
        worker_thread_.join();
    }
    std::lock_guard<std::mutex> lock(mutex_);
    state_ = FeedConnectionState::kDisconnected;
    error_message_.clear();
    width_ = 0;
    height_ = 0;
    frame_seq_ = 0;
    latest_frame_rgba_.clear();
}

bool RtspFeedReader::IsOpen() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return state_ == FeedConnectionState::kConnecting ||
           state_ == FeedConnectionState::kConnected;
}

FeedConnectionState RtspFeedReader::GetState() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return state_;
}

std::string RtspFeedReader::GetErrorMessage() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return error_message_;
}

std::string RtspFeedReader::GetUrl() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return url_;
}

int RtspFeedReader::GetWidth() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return width_;
}

int RtspFeedReader::GetHeight() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return height_;
}

uint64_t RtspFeedReader::GetFrameSequence() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return frame_seq_;
}

bool RtspFeedReader::CopyLatestFrameRgba(
    std::vector<uint8_t>& out_rgba,
    int& out_width,
    int& out_height,
    uint64_t& in_out_seq) const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (frame_seq_ == 0 || frame_seq_ == in_out_seq || latest_frame_rgba_.empty()) {
        return false;
    }
    out_rgba = latest_frame_rgba_;
    out_width = width_;
    out_height = height_;
    in_out_seq = frame_seq_;
    return true;
}

void RtspFeedReader::WorkerLoop(std::string url) {
#if !defined(_WIN32)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        state_ = FeedConnectionState::kError;
        error_message_ = "RTSP streaming is only supported on Windows.";
    }
    (void)url;
#else
    int w = 0;
    int h = 0;
    std::string probe_error;
    if (!ProbeRtspDimensions(url, w, h, probe_error, stop_requested_)) {
        if (!stop_requested_.load()) {
            std::lock_guard<std::mutex> lock(mutex_);
            state_ = FeedConnectionState::kError;
            error_message_ = probe_error;
        }
        return;
    }

    if (stop_requested_.load()) {
        return;
    }

    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;

    HANDLE read_pipe = nullptr;
    HANDLE write_pipe = nullptr;
    if (!CreatePipe(&read_pipe, &write_pipe, &sa, 0)) {
        std::lock_guard<std::mutex> lock(mutex_);
        state_ = FeedConnectionState::kError;
        error_message_ = "Failed to create pipe for ffmpeg.";
        return;
    }
    SetHandleInformation(read_pipe, HANDLE_FLAG_INHERIT, 0);

    std::ostringstream cmd;
    cmd << "ffmpeg -loglevel error -rtsp_transport tcp -fflags nobuffer "
        << "-flags low_delay -i " << QuoteArg(url)
        << " -an -sn -dn -vf scale=" << w << ":" << h
        << " -f rawvideo -pix_fmt rgba -";

    STARTUPINFOA si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = write_pipe;
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);

    PROCESS_INFORMATION pi{};
    std::string cmd_str = cmd.str();
    std::vector<char> cmd_buf(cmd_str.begin(), cmd_str.end());
    cmd_buf.push_back('\0');

    BOOL created = CreateProcessA(
        nullptr,
        cmd_buf.data(),
        nullptr,
        nullptr,
        TRUE,
        CREATE_NO_WINDOW,
        nullptr,
        nullptr,
        &si,
        &pi);
    CloseHandle(write_pipe);

    if (!created) {
        CloseHandle(read_pipe);
        std::lock_guard<std::mutex> lock(mutex_);
        state_ = FeedConnectionState::kError;
        error_message_ = "Failed to launch ffmpeg. Ensure FFmpeg is installed on PATH.";
        return;
    }

    {
        std::lock_guard<std::mutex> lock(process_mutex_);
        active_process_handle_ = pi.hProcess;
    }

    const size_t frame_bytes = static_cast<size_t>(w) * static_cast<size_t>(h) * 4;
    std::vector<uint8_t> frame_buf(frame_bytes);
    size_t offset = 0;

    while (!stop_requested_.load()) {
        DWORD bytes_read = 0;
        BOOL ok = ReadFile(
            read_pipe,
            frame_buf.data() + offset,
            static_cast<DWORD>(frame_bytes - offset),
            &bytes_read,
            nullptr);
        if (!ok || bytes_read == 0) {
            break;
        }
        offset += bytes_read;
        if (offset == frame_bytes) {
            offset = 0;
            std::lock_guard<std::mutex> lock(mutex_);
            width_ = w;
            height_ = h;
            latest_frame_rgba_ = frame_buf;
            ++frame_seq_;
            state_ = FeedConnectionState::kConnected;
            error_message_.clear();
        }
    }

    {
        std::lock_guard<std::mutex> lock(process_mutex_);
        active_process_handle_ = nullptr;
    }
    if (stop_requested_.load()) {
        TerminateProcess(pi.hProcess, 0);
    }
    WaitForSingleObject(pi.hProcess, 500);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    CloseHandle(read_pipe);

    if (!stop_requested_.load()) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (state_ != FeedConnectionState::kConnected) {
            state_ = FeedConnectionState::kError;
            error_message_ = "RTSP stream ended before receiving video frames.";
        } else {
            state_ = FeedConnectionState::kError;
            error_message_ = "RTSP stream disconnected.";
        }
    }
#endif
}

}  // namespace live_renderer
