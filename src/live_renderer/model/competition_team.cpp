/**
 * Implementation of CompetitionTeam model in LF Live Renderer.
 *
 * Provides storage and management for participating tournament teams,
 * including player roster manipulation and property accessors.
 *
 * Usage example:
 *   live_renderer::CompetitionTeam team;
 *   team.SetSlug("eagles");
 *   team.SetName("Golden Eagles");
 */

#include "live_renderer/model/competition_team.hpp"

#include <algorithm>

namespace live_renderer {

CompetitionTeam::CompetitionTeam() = default;

CompetitionTeam::CompetitionTeam(
    const std::string& slug,
    const std::string& name,
    const std::string& short_name,
    const std::string& logo_url,
    const std::vector<std::string>& players)
    : slug_(slug),
      name_(name),
      short_name_(short_name),
      logo_url_(logo_url),
      players_(players) {}

const std::string& CompetitionTeam::GetSlug() const {
    return slug_;
}

void CompetitionTeam::SetSlug(const std::string& slug) {
    slug_ = slug;
}

const std::string& CompetitionTeam::GetName() const {
    return name_;
}

void CompetitionTeam::SetName(const std::string& name) {
    name_ = name;
}

const std::string& CompetitionTeam::GetShortName() const {
    return short_name_;
}

void CompetitionTeam::SetShortName(const std::string& short_name) {
    short_name_ = short_name;
}

const std::string& CompetitionTeam::GetLogoUrl() const {
    return logo_url_;
}

void CompetitionTeam::SetLogoUrl(const std::string& logo_url) {
    logo_url_ = logo_url;
}

const std::vector<std::string>& CompetitionTeam::GetPlayers() const {
    return players_;
}

void CompetitionTeam::SetPlayers(const std::vector<std::string>& players) {
    players_ = players;
}

void CompetitionTeam::AddPlayer(const std::string& player) {
    players_.push_back(player);
}

bool CompetitionTeam::RemovePlayer(const std::string& player) {
    auto it = std::find(players_.begin(), players_.end(), player);
    if (it != players_.end()) {
        players_.erase(it);
        return true;
    }
    return false;
}

bool CompetitionTeam::HasPlayer(const std::string& player) const {
    return std::find(players_.begin(), players_.end(), player) !=
           players_.end();
}

bool CompetitionTeam::operator==(const CompetitionTeam& other) const {
    return slug_ == other.slug_ &&
           name_ == other.name_ &&
           short_name_ == other.short_name_ &&
           logo_url_ == other.logo_url_ &&
           players_ == other.players_;
}

bool CompetitionTeam::operator!=(const CompetitionTeam& other) const {
    return !(*this == other);
}

}  // namespace live_renderer

