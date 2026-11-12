/**
 * Implementation of LFStatsFetcher client in LF Live Renderer.
 *
 * Provides thread-safe HTTP querying, local fixture loading for tests,
 * JSON conversion to competition and scheduled game models, and background
 * task execution to prevent blocking render threads.
 *
 * Usage example:
 *   live_renderer::LFStatsFetcher fetcher(true, "tests/fixtures/lfstats");
 *   auto games = fetcher.FetchCompetitionSchedule("syracuse_trios_2026");
 */

#include "live_renderer/lfstats/lfstats_fetcher.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <yaml-cpp/yaml.h>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

namespace live_renderer {
namespace {

constexpr int64_t kDefaultGameDurationMs = 15 * 60 * 1000;  // 15 minutes

std::string TrimWhitespace(const std::string& s) {
    auto start = s.begin();
    while (start != s.end() &&
           std::isspace(static_cast<unsigned char>(*start))) {
        ++start;
    }
    auto end = s.end();
    do {
        --end;
    } while (std::distance(start, end) > 0 &&
             std::isspace(static_cast<unsigned char>(*end)));
    return std::string(start, end + 1);
}

std::optional<int64_t> ParseIsoDatetimeToMs(const std::string& iso_str) {
    if (iso_str.empty()) {
        return std::nullopt;
    }

    int year = 0, month = 0, day = 0, hour = 0, min = 0, sec = 0;
    int consumed = 0;
    if (std::sscanf(iso_str.c_str(), "%d-%d-%dT%d:%d:%d%n",
                    &year, &month, &day, &hour, &min, &sec,
                    &consumed) < 6) {
        return std::nullopt;
    }

    int frac_ms = 0;
    const char* ptr = iso_str.c_str() + consumed;
    if (*ptr == '.') {
        ++ptr;
        int divisor = 1000;
        int val = 0;
        while (std::isdigit(static_cast<unsigned char>(*ptr))) {
            val = val * 10 + (*ptr - '0');
            divisor /= 10;
            ++ptr;
        }
        frac_ms = (divisor > 0) ? (val * divisor) : (val / 10);
    }

    int tz_offset_ms = 0;
    if (*ptr == '+' || *ptr == '-') {
        char sign = *ptr++;
        int tz_h = 0, tz_m = 0;
        if (std::sscanf(ptr, "%d:%d", &tz_h, &tz_m) >= 1) {
            int total_mins = tz_h * 60 + tz_m;
            int offset = total_mins * 60 * 1000;
            tz_offset_ms = (sign == '+') ? offset : -offset;
        }
    }

    std::tm tm_utc{};
    tm_utc.tm_year = year - 1900;
    tm_utc.tm_mon = month - 1;
    tm_utc.tm_mday = day;
    tm_utc.tm_hour = hour;
    tm_utc.tm_min = min;
    tm_utc.tm_sec = sec;
    tm_utc.tm_isdst = 0;

#ifdef _WIN32
    time_t epoch_sec = _mkgmtime(&tm_utc);
#else
    time_t epoch_sec = timegm(&tm_utc);
#endif
    if (epoch_sec == static_cast<time_t>(-1)) {
        return std::nullopt;
    }

    int64_t total_ms = static_cast<int64_t>(epoch_sec) * 1000 +
                       frac_ms - tz_offset_ms;
    return total_ms;
}

#ifdef _WIN32
std::wstring Utf8ToWide(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()), nullptr, 0);
    std::wstring result(size_needed, 0);
    MultiByteToWideChar(
        CP_UTF8, 0, str.c_str(), static_cast<int>(str.size()),
        &result[0], size_needed);
    return result;
}

std::string WideToUtf8(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size_needed = WideCharToMultiByte(
        CP_UTF8, 0, wstr.c_str(), static_cast<int>(wstr.size()),
        nullptr, 0, nullptr, nullptr);
    std::string result(size_needed, 0);
    WideCharToMultiByte(
        CP_UTF8, 0, wstr.c_str(), static_cast<int>(wstr.size()),
        &result[0], size_needed, nullptr, nullptr);
    return result;
}

std::string DefaultWinHttpTransport(
    const std::string& url_str,
    const std::string& user_agent,
    const std::string& api_key,
    int64_t timeout_ms) {
    std::wstring wide_url = Utf8ToWide(url_str);
    std::wstring wide_ua = Utf8ToWide(user_agent);

    URL_COMPONENTS urlComp{};
    urlComp.dwStructSize = sizeof(urlComp);
    urlComp.dwSchemeLength = static_cast<DWORD>(-1);
    urlComp.dwHostNameLength = static_cast<DWORD>(-1);
    urlComp.dwUrlPathLength = static_cast<DWORD>(-1);
    urlComp.dwExtraInfoLength = static_cast<DWORD>(-1);

    if (!WinHttpCrackUrl(wide_url.c_str(), 0, 0, &urlComp)) {
        throw std::runtime_error("Invalid URL: " + url_str);
    }

    std::wstring host(urlComp.lpszHostName, urlComp.dwHostNameLength);
    std::wstring path(urlComp.lpszUrlPath, urlComp.dwUrlPathLength);
    if (urlComp.dwExtraInfoLength > 0) {
        path.append(urlComp.lpszExtraInfo, urlComp.dwExtraInfoLength);
    }

    HINTERNET hSession = WinHttpOpen(
        wide_ua.c_str(), WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) {
        throw std::runtime_error("WinHttpOpen failed");
    }

    DWORD dw_timeout = static_cast<DWORD>(timeout_ms);
    WinHttpSetTimeouts(hSession, dw_timeout, dw_timeout,
                       dw_timeout, dw_timeout);

    HINTERNET hConnect = WinHttpConnect(
        hSession, host.c_str(), urlComp.nPort, 0);
    if (!hConnect) {
        WinHttpCloseHandle(hSession);
        throw std::runtime_error("WinHttpConnect failed: " + url_str);
    }

    DWORD open_flags = (urlComp.nScheme == INTERNET_SCHEME_HTTPS)
                           ? WINHTTP_FLAG_SECURE
                           : 0;
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect, L"GET", path.c_str(), nullptr,
        WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, open_flags);
    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        throw std::runtime_error("WinHttpOpenRequest failed: " + url_str);
    }

    std::wstring headers = L"Accept: application/json\r\n";
    if (!api_key.empty()) {
        std::wstring wide_key = Utf8ToWide(api_key);
        headers += L"Authorization: Bearer " + wide_key + L"\r\n";
        headers += L"X-API-Key: " + wide_key + L"\r\n";
    }

    BOOL sent = WinHttpSendRequest(
        hRequest, headers.c_str(), static_cast<DWORD>(-1),
        nullptr, 0, 0, 0);
    if (!sent || !WinHttpReceiveResponse(hRequest, nullptr)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        throw std::runtime_error("WinHttp request failed: " + url_str);
    }

    DWORD status_code = 0;
    DWORD status_size = sizeof(status_code);
    WinHttpQueryHeaders(
        hRequest,
        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX, &status_code, &status_size,
        WINHTTP_NO_HEADER_INDEX);

    if (status_code != 200) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        throw std::runtime_error(
            "HTTP " + std::to_string(status_code) + " from " + url_str);
    }

    std::string response;
    DWORD bytes_available = 0;
    while (WinHttpQueryDataAvailable(hRequest, &bytes_available) &&
           bytes_available > 0) {
        std::vector<char> buffer(bytes_available);
        DWORD bytes_read = 0;
        if (WinHttpReadData(hRequest, buffer.data(), bytes_available,
                            &bytes_read) && bytes_read > 0) {
            response.append(buffer.data(), bytes_read);
        }
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return response;
}

std::string DefaultWinHttpTransport(
    const std::string& url_str,
    const std::string& user_agent,
    int64_t timeout_ms) {
    return DefaultWinHttpTransport(url_str, user_agent, "", timeout_ms);
}
#endif

ScheduledGame ConvertNodeToScheduledGame(const YAML::Node& item) {
    std::string game_name;
    if (item["gameName"] && !item["gameName"].IsNull()) {
        game_name = item["gameName"].as<std::string>();
    }

    std::optional<int> round_num;
    std::optional<int> match_num;
    std::optional<int> game_num;
    std::string stage = "G";
    ScheduledGame::ParseGameName(
        game_name, round_num, match_num, game_num, stage);

    std::optional<int64_t> start_ms;
    if (item["scheduledStartTime"] && !item["scheduledStartTime"].IsNull()) {
        start_ms = ParseIsoDatetimeToMs(
            item["scheduledStartTime"].as<std::string>());
    }
    if (!start_ms.has_value() && item["actualStartTime"] &&
        !item["actualStartTime"].IsNull()) {
        start_ms = ParseIsoDatetimeToMs(
            item["actualStartTime"].as<std::string>());
    }
    if (!start_ms.has_value()) {
        throw std::runtime_error(
            "Cannot determine start_time for game '" + game_name + "'.");
    }

    std::optional<int64_t> end_ms;
    if (item["scheduledEndTime"] && !item["scheduledEndTime"].IsNull()) {
        end_ms = ParseIsoDatetimeToMs(
            item["scheduledEndTime"].as<std::string>());
    }
    if (!end_ms.has_value()) {
        end_ms = *start_ms + kDefaultGameDurationMs;
    }

    std::string team1_name =
        (item["team1Name"] && !item["team1Name"].IsNull())
            ? item["team1Name"].as<std::string>()
            : "";
    std::string team2_name =
        (item["team2Name"] && !item["team2Name"].IsNull())
            ? item["team2Name"].as<std::string>()
            : "";
    std::vector<std::string> team_names = {team1_name, team2_name};

    std::string team1_logo =
        (item["team1LogoUrl"] && !item["team1LogoUrl"].IsNull())
            ? item["team1LogoUrl"].as<std::string>()
            : "";
    std::string team2_logo =
        (item["team2LogoUrl"] && !item["team2LogoUrl"].IsNull())
            ? item["team2LogoUrl"].as<std::string>()
            : "";
    std::vector<std::string> team_logos = {team1_logo, team2_logo};

    std::optional<std::vector<int>> team_scores;
    if (item["team1Score"] && !item["team1Score"].IsNull() &&
        item["team2Score"] && !item["team2Score"].IsNull()) {
        team_scores = std::vector<int>{
            item["team1Score"].as<int>(),
            item["team2Score"].as<int>()
        };
    }

    return ScheduledGame(
        game_name, team_names, team_logos,
        start_ms, end_ms, round_num, match_num, game_num, stage,
        team_scores);
}

std::string SlugifyTeamName(const std::string& name) {
    std::string result;
    for (char c : name) {
        if (std::isalnum(static_cast<unsigned char>(c))) {
            result += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        } else if (!result.empty() && result.back() != '_') {
            result += '_';
        }
    }
    while (!result.empty() && result.back() == '_') {
        result.pop_back();
    }
    return result.empty() ? "team" : result;
}

std::string DeriveTeamShortName(const std::string& name) {
    std::vector<std::string> words;
    std::string current;
    for (char c : name) {
        if (std::isalnum(static_cast<unsigned char>(c))) {
            current += c;
        } else if (!current.empty()) {
            words.push_back(current);
            current.clear();
        }
    }
    if (!current.empty()) {
        words.push_back(current);
    }
    if (words.size() >= 2) {
        std::string initials;
        for (const auto& w : words) {
            initials += static_cast<char>(std::toupper(static_cast<unsigned char>(w[0])));
            if (initials.size() == 4) break;
        }
        return initials;
    }
    std::string alpha;
    for (char c : name) {
        if (std::isalnum(static_cast<unsigned char>(c))) {
            alpha += static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
            if (alpha.size() == 4) break;
        }
    }
    return alpha.empty() ? "TEAM" : alpha;
}

std::vector<CompetitionTeam> ConvertNodeToCompetitionTeams(
    const YAML::Node& root, const std::string& competition_slug) {
    YAML::Node entries;
    if (root.IsMap()) {
        if (root[competition_slug] && root[competition_slug].IsSequence()) {
            entries = root[competition_slug];
        } else if (root.size() == 1 && root.begin()->second.IsSequence()) {
            entries = root.begin()->second;
        } else {
            throw std::runtime_error("Expected competition team stats key or list.");
        }
    } else if (root.IsSequence()) {
        entries = root;
    } else {
        throw std::runtime_error("Expected list or map for competition stats.");
    }

    struct TeamData {
        std::string team_name;
        std::string logo_url;
        std::vector<std::string> players;
    };
    std::vector<std::string> team_order;
    std::vector<TeamData> teams;

    for (size_t i = 0; i < entries.size(); ++i) {
        const auto& item = entries[i];
        if (!item.IsMap()) continue;

        std::string team_name;
        if (item["team_name"] && !item["team_name"].IsNull()) {
            team_name = TrimWhitespace(item["team_name"].as<std::string>());
        }
        if (team_name.empty()) continue;

        std::string player_name;
        if (item["player_name"] && !item["player_name"].IsNull()) {
            player_name = TrimWhitespace(item["player_name"].as<std::string>());
        }

        std::string team_logo_url;
        if (item["team_logo_url"] && !item["team_logo_url"].IsNull()) {
            team_logo_url = TrimWhitespace(item["team_logo_url"].as<std::string>());
        }

        auto it = std::find(team_order.begin(), team_order.end(), team_name);
        if (it == team_order.end()) {
            team_order.push_back(team_name);
            TeamData td;
            td.team_name = team_name;
            td.logo_url = team_logo_url;
            if (!player_name.empty()) {
                td.players.push_back(player_name);
            }
            teams.push_back(std::move(td));
        } else {
            size_t idx = std::distance(team_order.begin(), it);
            if (teams[idx].logo_url.empty() && !team_logo_url.empty()) {
                teams[idx].logo_url = team_logo_url;
            }
            if (!player_name.empty()) {
                const auto& p_list = teams[idx].players;
                if (std::find(p_list.begin(), p_list.end(), player_name) == p_list.end()) {
                    teams[idx].players.push_back(player_name);
                }
            }
        }
    }

    std::vector<CompetitionTeam> result;
    result.reserve(teams.size());
    for (const auto& td : teams) {
        std::string slug = SlugifyTeamName(td.team_name);
        std::string short_name = DeriveTeamShortName(td.team_name);
        result.emplace_back(slug, td.team_name, short_name, td.logo_url, td.players);
    }
    return result;
}

std::vector<CompetitionPlayerInfo> ConvertNodeToCompetitionPlayers(
    const YAML::Node& root, const std::string& competition_slug) {
    YAML::Node entries;
    if (root.IsMap()) {
        if (root[competition_slug] && root[competition_slug].IsSequence()) {
            entries = root[competition_slug];
        } else if (root.size() == 1 && root.begin()->second.IsSequence()) {
            entries = root.begin()->second;
        } else {
            throw std::runtime_error("Expected competition stats key or list.");
        }
    } else if (root.IsSequence()) {
        entries = root;
    } else {
        throw std::runtime_error("Expected list or map for competition stats.");
    }

    std::vector<CompetitionPlayerInfo> result;
    for (size_t i = 0; i < entries.size(); ++i) {
        const auto& item = entries[i];
        if (!item.IsMap()) continue;

        CompetitionPlayerInfo p;
        if (item["ipl_id"] && !item["ipl_id"].IsNull()) {
            p.entity_id = TrimWhitespace(item["ipl_id"].as<std::string>());
        }
        if (item["player_name"] && !item["player_name"].IsNull()) {
            p.player_name = TrimWhitespace(item["player_name"].as<std::string>());
        }
        if (item["player_picture_url"] && !item["player_picture_url"].IsNull()) {
            p.picture_url = TrimWhitespace(item["player_picture_url"].as<std::string>());
        }
        if (item["team_name"] && !item["team_name"].IsNull()) {
            p.team_name = TrimWhitespace(item["team_name"].as<std::string>());
        }
        if (item["team_logo_url"] && !item["team_logo_url"].IsNull()) {
            p.team_logo_url = TrimWhitespace(item["team_logo_url"].as<std::string>());
        }
        if (!p.entity_id.empty() || !p.player_name.empty()) {
            result.push_back(std::move(p));
        }
    }
    return result;
}

}  // namespace

LFStatsFetcher::LFStatsFetcher()
    : LFStatsFetcher(LFStatsFetcherOptions()) {}

LFStatsFetcher::LFStatsFetcher(const LFStatsFetcherOptions& options)
    : options_(options) {
    size_t num_threads = std::max<size_t>(1, options_.worker_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back([this]() {
            while (true) {
                std::function<void()> task;
                {
                    std::unique_lock<std::mutex> lock(queue_mutex_);
                    cv_.wait(lock, [this]() {
                        return stop_workers_ || !task_queue_.empty();
                    });
                    if (stop_workers_ && task_queue_.empty()) {
                        return;
                    }
                    task = std::move(task_queue_.front());
                    task_queue_.pop();
                    ++active_tasks_;
                }
                try {
                    task();
                } catch (...) {
                    // Task packaged_task stores exceptions
                }
                --active_tasks_;
            }
        });
    }
}

LFStatsFetcher::LFStatsFetcher(
    bool test_mode,
    const std::string& test_data_dir)
    : LFStatsFetcher([&]() {
          LFStatsFetcherOptions opts;
          opts.test_mode = test_mode;
          opts.test_data_dir = ResolveDefaultTestDataDir(test_data_dir);
          return opts;
      }()) {}

LFStatsFetcher::~LFStatsFetcher() {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        stop_workers_ = true;
    }
    cv_.notify_all();
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

void LFStatsFetcher::SetHttpTransport(HttpTransport transport) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    http_transport_ = std::move(transport);
}

void LFStatsFetcher::SetHttpTransport(HttpTransportWithKey transport) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    http_transport_with_key_ = std::move(transport);
}

std::string LFStatsFetcher::GetApiKey() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.api_key;
}

void LFStatsFetcher::SetApiKey(const std::string& api_key) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.api_key = api_key;
}

bool LFStatsFetcher::IsTestMode() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.test_mode;
}

void LFStatsFetcher::SetTestMode(bool test_mode) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.test_mode = test_mode;
}

const std::string& LFStatsFetcher::GetTestDataDir() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.test_data_dir;
}

void LFStatsFetcher::SetTestDataDir(const std::string& dir) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.test_data_dir = dir;
}

const std::vector<std::string>& LFStatsFetcher::GetDefaultTestDataPaths() {
    static const std::vector<std::string> kDefaultPaths = {
        "tests/fixtures/lfstats",
        "tests/fixtures",
        "../tests/fixtures/lfstats",
        "../tests/fixtures",
        "../../tests/fixtures/lfstats",
        "../../tests/fixtures",
        "../../../tests/fixtures/lfstats",
        "../../../tests/fixtures"
    };
    return kDefaultPaths;
}

std::string LFStatsFetcher::ResolveDefaultTestDataDir(
    const std::string& preferred) {
    if (!preferred.empty()) {
        std::filesystem::path pref_path(preferred);
        if (std::filesystem::exists(pref_path) &&
            std::filesystem::is_directory(pref_path)) {
            return preferred;
        }
    }

    for (const auto& path_str : GetDefaultTestDataPaths()) {
        std::filesystem::path p(path_str);
        if (std::filesystem::exists(p) && std::filesystem::is_directory(p)) {
            if (std::filesystem::exists(p / "competitions.json") ||
                std::filesystem::exists(p / "competitions")) {
                return path_str;
            }
        }
    }

    return "tests/fixtures/lfstats";
}

const std::string& LFStatsFetcher::GetBaseUrl() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.base_url;
}

void LFStatsFetcher::SetBaseUrl(const std::string& url) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.base_url = url;
}

int64_t LFStatsFetcher::GetTimeoutMs() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.timeout_ms;
}

void LFStatsFetcher::SetTimeoutMs(int64_t timeout_ms) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.timeout_ms = timeout_ms;
}

const std::string& LFStatsFetcher::GetUserAgent() const {
    std::lock_guard<std::mutex> lock(options_mutex_);
    return options_.user_agent;
}

void LFStatsFetcher::SetUserAgent(const std::string& user_agent) {
    std::lock_guard<std::mutex> lock(options_mutex_);
    options_.user_agent = user_agent;
}

size_t LFStatsFetcher::GetActiveTaskCount() const {
    return active_tasks_.load();
}

template <typename F>
auto LFStatsFetcher::EnqueueTask(F&& f)
    -> std::future<std::invoke_result_t<F>> {
    using ReturnType = std::invoke_result_t<F>;
    auto task_ptr = std::make_shared<std::packaged_task<ReturnType()>>(
        std::forward<F>(f));
    std::future<ReturnType> fut = task_ptr->get_future();
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        if (stop_workers_) {
            throw std::runtime_error("LFStatsFetcher worker pool is stopped.");
        }
        task_queue_.emplace([task_ptr]() { (*task_ptr)(); });
    }
    cv_.notify_one();
    return fut;
}

std::string LFStatsFetcher::FetchRemoteJson(const std::string& endpoint_path) {
    std::string base_url;
    std::string user_agent;
    std::string api_key;
    int64_t timeout_ms = 0;
    HttpTransport custom_transport;
    HttpTransportWithKey custom_transport_with_key;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        base_url = options_.base_url;
        user_agent = options_.user_agent;
        api_key = options_.api_key;
        timeout_ms = options_.timeout_ms;
        custom_transport = http_transport_;
        custom_transport_with_key = http_transport_with_key_;
    }

    while (!base_url.empty() && base_url.back() == '/') {
        base_url.pop_back();
    }
    std::string norm_path = (endpoint_path.empty() || endpoint_path[0] != '/')
                                ? ("/" + endpoint_path)
                                : endpoint_path;
    std::string full_url = base_url + norm_path;

    if (custom_transport_with_key) {
        return custom_transport_with_key(full_url, user_agent, api_key, timeout_ms);
    }
    if (custom_transport) {
        return custom_transport(full_url, user_agent, timeout_ms);
    }

#ifdef _WIN32
    return DefaultWinHttpTransport(full_url, user_agent, api_key, timeout_ms);
#else
    throw std::runtime_error(
        "Direct HTTP transport not implemented on non-Windows platforms.");
#endif
}

std::string LFStatsFetcher::LoadLocalFixture(
    const std::vector<std::string>& candidate_paths,
    const std::string& item_description) {
    for (const auto& path_str : candidate_paths) {
        std::filesystem::path p(path_str);
        std::vector<std::filesystem::path> attempts = {
            p,
            std::filesystem::path("..") / p,
            std::filesystem::path("../..") / p,
            std::filesystem::path("../../..") / p
        };
        for (const auto& attempt : attempts) {
            if (std::filesystem::exists(attempt) &&
                std::filesystem::is_regular_file(attempt)) {
                std::ifstream file(attempt, std::ios::in | std::ios::binary);
                if (file.is_open()) {
                    std::ostringstream ss;
                    ss << file.rdbuf();
                    return ss.str();
                }
            }
        }
    }

    for (const auto& def_dir : GetDefaultTestDataPaths()) {
        std::filesystem::path base(def_dir);
        for (const auto& path_str : candidate_paths) {
            std::filesystem::path p(path_str);
            std::filesystem::path filename = p.filename();
            std::vector<std::filesystem::path> attempts = {
                base / filename
            };
            if (p.has_parent_path()) {
                attempts.push_back(base / p.parent_path().filename() / filename);
            }
            for (const auto& attempt : attempts) {
                if (std::filesystem::exists(attempt) &&
                    std::filesystem::is_regular_file(attempt)) {
                    std::ifstream file(attempt, std::ios::in | std::ios::binary);
                    if (file.is_open()) {
                        std::ostringstream ss;
                        ss << file.rdbuf();
                        return ss.str();
                    }
                }
            }
        }
    }

    std::ostringstream searched;
    for (size_t i = 0; i < candidate_paths.size(); ++i) {
        if (i > 0) searched << ", ";
        searched << candidate_paths[i];
    }
    throw std::runtime_error(
        "No local fixture found for " + item_description +
        ". Checked: " + searched.str());
}

std::string LFStatsFetcher::FetchData(
    const std::string& endpoint_path,
    const std::vector<std::string>& candidate_paths,
    const std::string& item_description) {
    bool test_mode = false;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        test_mode = options_.test_mode;
    }
    if (test_mode) {
        return LoadLocalFixture(candidate_paths, item_description);
    }
    return FetchRemoteJson(endpoint_path);
}

std::vector<CompetitionInfo> LFStatsFetcher::FetchCompetitions() {
    std::string test_dir;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        test_dir = options_.test_data_dir;
    }

    std::filesystem::path base(test_dir);
    std::vector<std::string> candidates = {
        (base / "competitions.json").string(),
        (base / "competitions" / "competitions.json").string(),
        (base / "competitions" / "index.json").string()
    };

    std::string raw_json = FetchData(
        "/competitions", candidates, "competitions list");

    YAML::Node doc = YAML::Load(raw_json);
    YAML::Node items;
    if (doc.IsMap()) {
        if (!doc["data"] || !doc["data"].IsSequence()) {
            throw std::runtime_error("Expected 'data' field to be a list.");
        }
        items = doc["data"];
    } else if (doc.IsSequence()) {
        items = doc;
    } else {
        throw std::runtime_error(
            "Expected competitions response to be a map or sequence.");
    }

    std::vector<CompetitionInfo> results;
    for (size_t i = 0; i < items.size(); ++i) {
        const auto& item = items[i];
        if (!item.IsMap()) continue;
        std::string name =
            (item["name"] && !item["name"].IsNull())
                ? item["name"].as<std::string>()
                : "";
        std::string slug =
            (item["slug"] && !item["slug"].IsNull())
                ? item["slug"].as<std::string>()
                : "";
        if (!name.empty() || !slug.empty()) {
            results.emplace_back(name, slug);
        }
    }
    return results;
}

std::vector<CompetitionInfo> LFStatsFetcher::FetchAllCompetitions() {
    return FetchCompetitions();
}

std::vector<ScheduledGame> LFStatsFetcher::FetchCompetitionSchedule(
    const std::string& competition_slug) {
    std::string slug = TrimWhitespace(competition_slug);
    if (slug.empty()) {
        throw std::invalid_argument("competition_slug cannot be empty.");
    }

    std::string test_dir;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        test_dir = options_.test_data_dir;
    }

    std::filesystem::path base(test_dir);
    std::vector<std::string> candidates = {
        (base / "competitions" / slug / "schedule.json").string(),
        (base / slug / "schedule.json").string(),
        (base / (slug + "_schedule.json")).string(),
        (base / (slug + ".json")).string()
    };

    std::string raw_json = FetchData(
        "/competitions/" + slug + "/schedule",
        candidates,
        "schedule for '" + slug + "'");

    YAML::Node doc = YAML::Load(raw_json);
    if (!doc.IsSequence()) {
        throw std::runtime_error("Expected schedule data to be a list.");
    }

    std::vector<ScheduledGame> schedule;
    schedule.reserve(doc.size());
    for (size_t i = 0; i < doc.size(); ++i) {
        schedule.push_back(ConvertNodeToScheduledGame(doc[i]));
    }
    return schedule;
}

std::vector<ScheduledGame> LFStatsFetcher::FetchSchedule(
    const std::string& competition_slug) {
    return FetchCompetitionSchedule(competition_slug);
}

std::future<std::vector<CompetitionInfo>>
LFStatsFetcher::FetchCompetitionsAsync() {
    return EnqueueTask([this]() { return FetchCompetitions(); });
}

std::future<std::vector<CompetitionInfo>>
LFStatsFetcher::FetchAllCompetitionsAsync() {
    return FetchCompetitionsAsync();
}

std::future<std::vector<ScheduledGame>>
LFStatsFetcher::FetchCompetitionScheduleAsync(
    const std::string& competition_slug) {
    return EnqueueTask([this, competition_slug]() {
        return FetchCompetitionSchedule(competition_slug);
    });
}

std::future<std::vector<ScheduledGame>>
LFStatsFetcher::FetchScheduleAsync(const std::string& competition_slug) {
    return FetchCompetitionScheduleAsync(competition_slug);
}

void LFStatsFetcher::FetchCompetitionsAsync(CompetitionsCallback callback) {
    EnqueueTask([this, callback = std::move(callback)]() {
        try {
            auto result = FetchCompetitions();
            callback(result, "");
        } catch (const std::exception& e) {
            callback({}, e.what());
        } catch (...) {
            callback({}, "Unknown error occurred while fetching competitions.");
        }
    });
}

void LFStatsFetcher::FetchCompetitionScheduleAsync(
    const std::string& competition_slug,
    ScheduleCallback callback) {
    EnqueueTask([this, competition_slug, callback = std::move(callback)]() {
        try {
            auto result = FetchCompetitionSchedule(competition_slug);
            callback(result, "");
        } catch (const std::exception& e) {
            callback({}, e.what());
        } catch (...) {
            callback({}, "Unknown error occurred while fetching schedule.");
        }
    });
}

std::vector<CompetitionTeam> LFStatsFetcher::FetchCompetitionTeams(
    const std::string& competition_slug) {
    std::string slug = TrimWhitespace(competition_slug);
    if (slug.empty()) {
        throw std::invalid_argument("competition_slug cannot be empty.");
    }

    std::string test_dir;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        test_dir = options_.test_data_dir;
    }

    std::filesystem::path base(test_dir);
    std::vector<std::string> candidates = {
        (base / "competitions" / slug / "stats.json").string(),
        (base / "competitions" / slug / "teams.json").string(),
        (base / slug / "stats.json").string(),
        (base / slug / "teams.json").string(),
        (base / (slug + "_stats.json")).string(),
        (base / (slug + "_teams.json")).string()
    };

    std::string raw_json = FetchData(
        "/competitions/" + slug + "/stats",
        candidates,
        "team details for '" + slug + "'");

    YAML::Node doc = YAML::Load(raw_json);
    return ConvertNodeToCompetitionTeams(doc, slug);
}

std::vector<CompetitionTeam> LFStatsFetcher::FetchTeams(
    const std::string& competition_slug) {
    return FetchCompetitionTeams(competition_slug);
}

std::future<std::vector<CompetitionTeam>>
LFStatsFetcher::FetchCompetitionTeamsAsync(
    const std::string& competition_slug) {
    return EnqueueTask([this, competition_slug]() {
        return FetchCompetitionTeams(competition_slug);
    });
}

std::future<std::vector<CompetitionTeam>>
LFStatsFetcher::FetchTeamsAsync(const std::string& competition_slug) {
    return FetchCompetitionTeamsAsync(competition_slug);
}

void LFStatsFetcher::FetchCompetitionTeamsAsync(
    const std::string& competition_slug,
    TeamsCallback callback) {
    EnqueueTask([this, competition_slug, callback = std::move(callback)]() {
        try {
            auto result = FetchCompetitionTeams(competition_slug);
            callback(result, "");
        } catch (const std::exception& e) {
            callback({}, e.what());
        } catch (...) {
            callback({}, "Unknown error occurred while fetching team details.");
        }
    });
}

std::vector<CompetitionPlayerInfo> LFStatsFetcher::FetchCompetitionPlayerDetails(
    const std::string& competition_slug) {
    std::string slug = TrimWhitespace(competition_slug);
    if (slug.empty()) {
        throw std::invalid_argument("competition_slug cannot be empty.");
    }

    std::string test_dir;
    {
        std::lock_guard<std::mutex> lock(options_mutex_);
        test_dir = options_.test_data_dir;
    }

    std::filesystem::path base(test_dir);
    std::vector<std::string> candidates = {
        (base / "competitions" / slug / "stats.json").string(),
        (base / "competitions" / slug / "teams.json").string(),
        (base / slug / "stats.json").string(),
        (base / slug / "teams.json").string(),
        (base / (slug + "_stats.json")).string(),
        (base / (slug + "_teams.json")).string()
    };

    std::string raw_json = FetchData(
        "/competitions/" + slug + "/stats",
        candidates,
        "player details for '" + slug + "'");

    YAML::Node doc = YAML::Load(raw_json);
    return ConvertNodeToCompetitionPlayers(doc, slug);
}

std::future<std::vector<CompetitionPlayerInfo>>
LFStatsFetcher::FetchCompetitionPlayerDetailsAsync(
    const std::string& competition_slug) {
    return EnqueueTask([this, competition_slug]() {
        return FetchCompetitionPlayerDetails(competition_slug);
    });
}

void LFStatsFetcher::FetchCompetitionPlayerDetailsAsync(
    const std::string& competition_slug,
    PlayersCallback callback) {
    EnqueueTask([this, competition_slug, callback = std::move(callback)]() {
        try {
            auto result = FetchCompetitionPlayerDetails(competition_slug);
            callback(result, "");
        } catch (const std::exception& e) {
            callback({}, e.what());
        } catch (...) {
            callback({}, "Unknown error occurred while fetching player details.");
        }
    });
}

}  // namespace live_renderer
