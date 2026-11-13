/**
 * Implementation of ScheduledGame model in LF Live Renderer.
 *
 * Provides fixture tracking, game name parsing/formatting, score
 * recording, and score differential calculation for competition games.
 *
 * Usage example:
 *   live_renderer::ScheduledGame game;
 *   game.SetGameName("R2 M1 G1");
 *   game.SetTeamScores(std::vector<int>{12000, 9500});
 */

#include "live_renderer/model/scheduled_game.hpp"

#include <cmath>
#include <regex>
#include <sstream>

namespace live_renderer {

ScheduledGame::ScheduledGame() = default;

ScheduledGame::ScheduledGame(
    const std::string& game_name,
    const std::vector<std::string>& team_names,
    const std::vector<std::string>& team_logos,
    std::optional<int64_t> scheduled_start_time_ms,
    std::optional<int64_t> scheduled_end_time_ms,
    std::optional<int> round_number,
    std::optional<int> match_number,
    std::optional<int> game_number,
    const std::string& stage_indicator,
    std::optional<std::vector<int>> team_scores,
    std::optional<int64_t> actual_start_time_ms)
    : game_name_(game_name),
      team_names_(team_names),
      team_logos_(team_logos),
      scheduled_start_time_ms_(scheduled_start_time_ms),
      scheduled_end_time_ms_(scheduled_end_time_ms),
      actual_start_time_ms_(actual_start_time_ms),
      round_number_(round_number),
      match_number_(match_number),
      game_number_(game_number),
      stage_indicator_(stage_indicator),
      team_scores_(team_scores) {}

const std::string& ScheduledGame::GetGameName() const {
    return game_name_;
}

void ScheduledGame::SetGameName(const std::string& game_name) {
    game_name_ = game_name;
}

const std::vector<std::string>& ScheduledGame::GetTeamNames() const {
    return team_names_;
}

void ScheduledGame::SetTeamNames(const std::vector<std::string>& team_names) {
    team_names_ = team_names;
}

void ScheduledGame::AddTeamName(const std::string& team_name) {
    team_names_.push_back(team_name);
}

const std::vector<std::string>& ScheduledGame::GetTeamLogos() const {
    return team_logos_;
}

void ScheduledGame::SetTeamLogos(const std::vector<std::string>& team_logos) {
    team_logos_ = team_logos;
}

void ScheduledGame::AddTeamLogo(const std::string& logo_url) {
    team_logos_.push_back(logo_url);
}

const std::optional<int64_t>&
ScheduledGame::GetScheduledStartTimeMs() const {
    return scheduled_start_time_ms_;
}

void ScheduledGame::SetScheduledStartTimeMs(
    std::optional<int64_t> scheduled_start_time_ms) {
    scheduled_start_time_ms_ = scheduled_start_time_ms;
}

const std::optional<int64_t>&
ScheduledGame::GetScheduledEndTimeMs() const {
    return scheduled_end_time_ms_;
}

void ScheduledGame::SetScheduledEndTimeMs(
    std::optional<int64_t> scheduled_end_time_ms) {
    scheduled_end_time_ms_ = scheduled_end_time_ms;
}

const std::optional<int64_t>&
ScheduledGame::GetActualStartTimeMs() const {
    return actual_start_time_ms_;
}

void ScheduledGame::SetActualStartTimeMs(
    std::optional<int64_t> actual_start_time_ms) {
    actual_start_time_ms_ = actual_start_time_ms;
}

const std::optional<int>& ScheduledGame::GetRoundNumber() const {
    return round_number_;
}

void ScheduledGame::SetRoundNumber(std::optional<int> round_number) {
    round_number_ = round_number;
}

const std::optional<int>& ScheduledGame::GetMatchNumber() const {
    return match_number_;
}

void ScheduledGame::SetMatchNumber(std::optional<int> match_number) {
    match_number_ = match_number;
}

const std::optional<int>& ScheduledGame::GetGameNumber() const {
    return game_number_;
}

void ScheduledGame::SetGameNumber(std::optional<int> game_number) {
    game_number_ = game_number;
}

const std::string& ScheduledGame::GetStageIndicator() const {
    return stage_indicator_;
}

void ScheduledGame::SetStageIndicator(const std::string& stage_indicator) {
    stage_indicator_ = stage_indicator;
}

const std::optional<std::vector<int>>&
ScheduledGame::GetTeamScores() const {
    return team_scores_;
}

void ScheduledGame::SetTeamScores(
    std::optional<std::vector<int>> team_scores) {
    team_scores_ = team_scores;
}

bool ScheduledGame::IsComplete() const {
    return team_scores_.has_value() && !team_scores_->empty();
}

std::optional<int> ScheduledGame::GetScoreDifferential() const {
    if (!team_scores_.has_value() || team_scores_->size() < 2) {
        return std::nullopt;
    }
    return std::abs((*team_scores_)[0] - (*team_scores_)[1]);
}

std::string ScheduledGame::FormatGameName(
    std::optional<int> round_number,
    std::optional<int> match_number,
    std::optional<int> game_number,
    const std::string& stage_indicator) {
    std::vector<std::string> parts;
    if (round_number.has_value()) {
        parts.push_back("R" + std::to_string(*round_number));
    }
    if (match_number.has_value()) {
        parts.push_back("M" + std::to_string(*match_number));
    }
    if (game_number.has_value()) {
        parts.push_back(stage_indicator + std::to_string(*game_number));
    }
    std::ostringstream oss;
    for (size_t i = 0; i < parts.size(); ++i) {
        if (i > 0) {
            oss << " ";
        }
        oss << parts[i];
    }
    return oss.str();
}

void ScheduledGame::ParseGameName(
    const std::string& game_name,
    std::optional<int>& out_round,
    std::optional<int>& out_match,
    std::optional<int>& out_game,
    std::string& out_stage) {
    out_round = std::nullopt;
    out_match = std::nullopt;
    out_game = std::nullopt;
    out_stage = "G";

    std::regex round_regex(R"(\bR(\d+)\b)");
    std::smatch match;
    if (std::regex_search(game_name, match, round_regex)) {
        out_round = std::stoi(match[1].str());
    }

    std::regex match_regex(R"(\bM(\d+)\b)");
    if (std::regex_search(game_name, match, match_regex)) {
        out_match = std::stoi(match[1].str());
    }

    std::regex stage_regex(R"(\b([A-Za-z]+)(\d+)\b)");
    auto words_begin = std::sregex_iterator(
        game_name.begin(), game_name.end(), stage_regex);
    auto words_end = std::sregex_iterator();
    for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
        std::smatch sm = *i;
        std::string prefix = sm[1].str();
        if (prefix != "R" && prefix != "M") {
            out_stage = prefix;
            out_game = std::stoi(sm[2].str());
            break;
        }
    }
}

bool ScheduledGame::operator==(const ScheduledGame& other) const {
    return game_name_ == other.game_name_ &&
           team_names_ == other.team_names_ &&
           team_logos_ == other.team_logos_ &&
           scheduled_start_time_ms_ == other.scheduled_start_time_ms_ &&
           scheduled_end_time_ms_ == other.scheduled_end_time_ms_ &&
           actual_start_time_ms_ == other.actual_start_time_ms_ &&
           round_number_ == other.round_number_ &&
           match_number_ == other.match_number_ &&
           game_number_ == other.game_number_ &&
           stage_indicator_ == other.stage_indicator_ &&
           team_scores_ == other.team_scores_;
}

bool ScheduledGame::operator!=(const ScheduledGame& other) const {
    return !(*this == other);
}

}  // namespace live_renderer

