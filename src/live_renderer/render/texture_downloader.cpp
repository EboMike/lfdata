/**
 * @file texture_downloader.cpp
 * @brief Implementation of TextureDownloader for HTTP/HTTPS image downloading.
 */

#include "live_renderer/render/texture_downloader.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

namespace live_renderer {
namespace {

std::string Utf8ToWideString(const std::string& str) {
#ifdef _WIN32
    if (str.empty()) return "";
    int len = MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()), nullptr, 0);
    std::wstring result(len, 0);
    MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()),
        &result[0], len);
    return std::string(
        reinterpret_cast<const char*>(result.data()),
        result.size() * sizeof(wchar_t));
#else
    return str;
#endif
}

std::string ComputeUrlHash(const std::string& url) {
    uint64_t hash = 14695981039346656037ULL;
    for (char c : url) {
        hash ^= static_cast<uint8_t>(c);
        hash *= 1099511628211ULL;
    }
    std::ostringstream oss;
    oss << std::hex << std::setfill('0') << std::setw(16) << hash;
    return oss.str();
}

std::string ExtractExtension(const std::string& url) {
    auto qpos = url.find('?');
    std::string base = (qpos != std::string::npos) ? url.substr(0, qpos) : url;
    auto dotpos = base.rfind('.');
    if (dotpos != std::string::npos && dotpos + 1 < base.size()) {
        std::string ext = base.substr(dotpos);
        if (ext == ".png" || ext == ".jpg" || ext == ".jpeg" ||
            ext == ".bmp" || ext == ".webp") {
            return ext;
        }
    }
    return ".png";
}

}  // namespace

TextureDownloader::TextureDownloader(
    std::string cache_dir,
    HttpImageFetchFn custom_fetcher)
    : cache_dir_(std::move(cache_dir)),
      custom_fetcher_(std::move(custom_fetcher)) {
    try {
        std::filesystem::create_directories(cache_dir_);
    } catch (...) {}
}

TextureDownloader::~TextureDownloader() = default;

bool TextureDownloader::IsHttpUrl(const std::string& path) {
    return path.rfind("http://", 0) == 0 || path.rfind("https://", 0) == 0;
}

std::string TextureDownloader::GetCacheFilename(const std::string& url) const {
    return ComputeUrlHash(url) + ExtractExtension(url);
}

std::string TextureDownloader::GetCachedFilePath(const std::string& url) const {
    namespace fs = std::filesystem;
    fs::path p = fs::path(cache_dir_) / GetCacheFilename(url);
    if (fs::exists(p) && fs::file_size(p) > 0) {
        return p.string();
    }
    return "";
}

bool TextureDownloader::HasFailed(const std::string& url) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return failed_urls_.contains(url);
}

void TextureDownloader::SetCustomFetcher(HttpImageFetchFn fetcher) {
    custom_fetcher_ = std::move(fetcher);
}

std::string TextureDownloader::DownloadSync(const std::string& url) {
    if (!IsHttpUrl(url)) {
        return "";
    }

    std::string existing = GetCachedFilePath(url);
    if (!existing.empty()) {
        return existing;
    }

    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (failed_urls_.contains(url)) {
            return "";
        }
    }

    std::vector<uint8_t> bytes;
    if (custom_fetcher_) {
        bytes = custom_fetcher_(url);
    } else {
        bytes = DefaultWinHttpDownload(url);
    }

    if (bytes.empty()) {
        std::lock_guard<std::mutex> lock(mutex_);
        failed_urls_.insert(url);
        return "";
    }

    namespace fs = std::filesystem;
    try {
        fs::create_directories(cache_dir_);
        fs::path target = fs::path(cache_dir_) / GetCacheFilename(url);
        std::ofstream out(target, std::ios::binary);
        if (!out) {
            return "";
        }
        out.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
        out.close();
        return target.string();
    } catch (...) {
        return "";
    }
}

void TextureDownloader::RequestDownloadAsync(const std::string& url) {
    if (!IsHttpUrl(url)) return;

    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (failed_urls_.contains(url) || pending_urls_.contains(url)) {
            return;
        }
        std::string existing = GetCachedFilePath(url);
        if (!existing.empty()) {
            completed_downloads_.push_back({url, existing});
            return;
        }
        pending_urls_.insert(url);
    }

    std::thread([this, url]() {
        std::string cached = DownloadSync(url);
        std::lock_guard<std::mutex> lock(mutex_);
        pending_urls_.erase(url);
        if (!cached.empty()) {
            completed_downloads_.push_back({url, cached});
        } else {
            failed_urls_.insert(url);
        }
    }).detach();
}

void TextureDownloader::PollCompletedDownloads(
    const std::function<void(
        const std::string& url,
        const std::string& cached_path)>& on_complete) {
    std::vector<std::pair<std::string, std::string>> ready;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        ready.swap(completed_downloads_);
    }
    for (const auto& [url, path] : ready) {
        on_complete(url, path);
    }
}

std::vector<uint8_t> TextureDownloader::DefaultWinHttpDownload(
    const std::string& url) {
#ifdef _WIN32
    std::string wide_url_bytes = Utf8ToWideString(url);
    const wchar_t* wide_url =
        reinterpret_cast<const wchar_t*>(wide_url_bytes.data());

    URL_COMPONENTS comp{};
    comp.dwStructSize = sizeof(comp);
    comp.dwSchemeLength = static_cast<DWORD>(-1);
    comp.dwHostNameLength = static_cast<DWORD>(-1);
    comp.dwUrlPathLength = static_cast<DWORD>(-1);
    comp.dwExtraInfoLength = static_cast<DWORD>(-1);

    if (!WinHttpCrackUrl(wide_url, 0, 0, &comp)) {
        return {};
    }

    std::wstring host(comp.lpszHostName, comp.dwHostNameLength);
    std::wstring path(comp.lpszUrlPath, comp.dwUrlPathLength);
    if (comp.dwExtraInfoLength > 0) {
        path.append(comp.lpszExtraInfo, comp.dwExtraInfoLength);
    }

    HINTERNET hSession = WinHttpOpen(
        L"live_renderer/0.1.43",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0);
    if (!hSession) return {};

    DWORD timeout = 8000;
    WinHttpSetTimeouts(hSession, timeout, timeout, timeout, timeout);

    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), comp.nPort, 0);
    if (!hConnect) {
        WinHttpCloseHandle(hSession);
        return {};
    }

    DWORD flags = (comp.nScheme == INTERNET_SCHEME_HTTPS)
                      ? WINHTTP_FLAG_SECURE
                      : 0;
    HINTERNET hReq = WinHttpOpenRequest(
        hConnect, L"GET", path.c_str(), nullptr,
        WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, flags);
    if (!hReq) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return {};
    }

    BOOL sent = WinHttpSendRequest(
        hReq, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
        WINHTTP_NO_REQUEST_DATA, 0, 0, 0);
    if (!sent || !WinHttpReceiveResponse(hReq, nullptr)) {
        WinHttpCloseHandle(hReq);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return {};
    }

    DWORD status_code = 0;
    DWORD status_size = sizeof(status_code);
    WinHttpQueryHeaders(
        hReq,
        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX,
        &status_code,
        &status_size,
        WINHTTP_NO_HEADER_INDEX);

    if (status_code != 200) {
        WinHttpCloseHandle(hReq);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return {};
    }

    std::vector<uint8_t> result;
    DWORD bytes_avail = 0;
    while (WinHttpQueryDataAvailable(hReq, &bytes_avail) && bytes_avail > 0) {
        size_t prev_size = result.size();
        result.resize(prev_size + bytes_avail);
        DWORD bytes_read = 0;
        if (WinHttpReadData(
                hReq, result.data() + prev_size, bytes_avail, &bytes_read) &&
            bytes_read > 0) {
            result.resize(prev_size + bytes_read);
        } else {
            result.resize(prev_size);
            break;
        }
    }

    WinHttpCloseHandle(hReq);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return result;
#else
    return {};
#endif
}

}  // namespace live_renderer

