/**
 * Implementation of CompetitionInfo model in LF Live Renderer.
 *
 * Provides accessors and equality comparison for competition metadata.
 *
 * Usage example:
 *   live_renderer::CompetitionInfo comp("Autumn Cup", "autumn_cup");
 *   assert(comp.GetSlug() == "autumn_cup");
 */

#include "live_renderer/lfstats/competition_info.hpp"

namespace live_renderer {

CompetitionInfo::CompetitionInfo() = default;

CompetitionInfo::CompetitionInfo(
    const std::string& name,
    const std::string& slug)
    : name_(name), slug_(slug) {}

const std::string& CompetitionInfo::GetName() const {
    return name_;
}

void CompetitionInfo::SetName(const std::string& name) {
    name_ = name;
}

const std::string& CompetitionInfo::GetSlug() const {
    return slug_;
}

void CompetitionInfo::SetSlug(const std::string& slug) {
    slug_ = slug;
}

bool CompetitionInfo::operator==(const CompetitionInfo& other) const {
    return name_ == other.name_ && slug_ == other.slug_;
}

bool CompetitionInfo::operator!=(const CompetitionInfo& other) const {
    return !(*this == other);
}

}  // namespace live_renderer

