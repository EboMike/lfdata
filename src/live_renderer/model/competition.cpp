/**
 * Implementation of Competition model in LF Live Renderer.
 *
 * Provides tournament event tracking, team roster lookups, schedule
 * management, and completion statistics.
 *
 * Usage example:
 *   live_renderer::Competition comp("LF Australian Nationals 2026");
 *   comp.SetSite("Brisbane");
 *   comp.AddTeam(live_renderer::CompetitionTeam("rebels", "Rebels", "REB"));
 */

#include "live_renderer/model/competition.hpp"

#include <algorithm>

namespace live_renderer {

Competition::Competition() = default;

Competition::Competition(
    const std::string& name,
    const std::string& slug,
    const std::string& site,
    std::optional<int64_t> start_time_ms,
    std::optional<int64_t> end_time_ms,
    const std::vector<CompetitionTeam>& teams,
    const std::vector<ScheduledGame>& schedule)
    : name_(name),
      slug_(slug),
      site_(site),
      start_time_ms_(start_time_ms),
      end_time_ms_(end_time_ms),
      teams_(teams),
      schedule_(schedule) {}

const std::string& Competition::GetName() const {
    return name_;
}

void Competition::SetName(const std::string& name) {
    name_ = name;
}

const std::string& Competition::GetSlug() const {
    return slug_;
}

void Competition::SetSlug(const std::string& slug) {
    slug_ = slug;
}

const std::string& Competition::GetSite() const {
    return site_;
}

void Competition::SetSite(const std::string& site) {
    site_ = site;
}

const std::optional<int64_t>& Competition::GetStartTimeMs() const {
    return start_time_ms_;
}

void Competition::SetStartTimeMs(std::optional<int64_t> start_time_ms) {
    start_time_ms_ = start_time_ms;
}

const std::optional<int64_t>& Competition::GetEndTimeMs() const {
    return end_time_ms_;
}

void Competition::SetEndTimeMs(std::optional<int64_t> end_time_ms) {
    end_time_ms_ = end_time_ms;
}

const std::vector<CompetitionTeam>& Competition::GetTeams() const {
    return teams_;
}

void Competition::SetTeams(const std::vector<CompetitionTeam>& teams) {
    teams_ = teams;
}

void Competition::AddTeam(const CompetitionTeam& team) {
    teams_.push_back(team);
}

bool Competition::RemoveTeam(const std::string& slug) {
    auto it = std::find_if(
        teams_.begin(), teams_.end(),
        [&slug](const CompetitionTeam& t) { return t.GetSlug() == slug; });
    if (it == teams_.end()) {
        return false;
    }
    teams_.erase(it);
    return true;
}

const CompetitionTeam* Competition::FindTeam(const std::string& slug) const {
    auto it = std::find_if(
        teams_.begin(), teams_.end(),
        [&slug](const CompetitionTeam& t) { return t.GetSlug() == slug; });
    if (it == teams_.end()) {
        return nullptr;
    }
    return &(*it);
}

CompetitionTeam* Competition::FindTeam(const std::string& slug) {
    auto it = std::find_if(
        teams_.begin(), teams_.end(),
        [&slug](const CompetitionTeam& t) { return t.GetSlug() == slug; });
    if (it == teams_.end()) {
        return nullptr;
    }
    return &(*it);
}

bool Competition::HasTeam(const std::string& slug) const {
    return FindTeam(slug) != nullptr;
}

const std::vector<ScheduledGame>& Competition::GetSchedule() const {
    return schedule_;
}

void Competition::SetSchedule(const std::vector<ScheduledGame>& schedule) {
    schedule_ = schedule;
}

void Competition::AddScheduledGame(const ScheduledGame& game) {
    schedule_.push_back(game);
}

bool Competition::RemoveScheduledGame(size_t index) {
    if (index >= schedule_.size()) {
        return false;
    }
    schedule_.erase(schedule_.begin() + index);
    return true;
}

const ScheduledGame* Competition::FindScheduledGame(
    const std::string& game_name) const {
    auto it = std::find_if(
        schedule_.begin(), schedule_.end(),
        [&game_name](const ScheduledGame& g) {
            return g.GetGameName() == game_name;
        });
    if (it == schedule_.end()) {
        return nullptr;
    }
    return &(*it);
}

ScheduledGame* Competition::FindScheduledGame(
    const std::string& game_name) {
    auto it = std::find_if(
        schedule_.begin(), schedule_.end(),
        [&game_name](const ScheduledGame& g) {
            return g.GetGameName() == game_name;
        });
    if (it == schedule_.end()) {
        return nullptr;
    }
    return &(*it);
}

std::vector<const ScheduledGame*> Competition::GetGamesForTeam(
    const std::string& team_name) const {
    std::vector<const ScheduledGame*> result;
    for (const auto& game : schedule_) {
        const auto& names = game.GetTeamNames();
        if (std::find(names.begin(), names.end(), team_name) != names.end()) {
            result.push_back(&game);
        }
    }
    return result;
}

size_t Competition::GetTotalGamesCount() const {
    return schedule_.size();
}

size_t Competition::GetCompletedGamesCount() const {
    return std::count_if(
        schedule_.begin(), schedule_.end(),
        [](const ScheduledGame& g) { return g.IsComplete(); });
}

bool Competition::operator==(const Competition& other) const {
    return name_ == other.name_ &&
           slug_ == other.slug_ &&
           site_ == other.site_ &&
           start_time_ms_ == other.start_time_ms_ &&
           end_time_ms_ == other.end_time_ms_ &&
           teams_ == other.teams_ &&
           schedule_ == other.schedule_;
}

bool Competition::operator!=(const Competition& other) const {
    return !(*this == other);
}

}  // namespace live_renderer

