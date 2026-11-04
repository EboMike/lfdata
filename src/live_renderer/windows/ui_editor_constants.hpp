#ifndef LIVE_RENDERER_WINDOWS_UI_EDITOR_CONSTANTS_HPP_
#define LIVE_RENDERER_WINDOWS_UI_EDITOR_CONSTANTS_HPP_

namespace live_renderer {

inline constexpr const char* const kTopLevelElementTypes[] = {
    "user_text",
    "game_timer",
    "user_image",
    "movie",
    "team_scorecard",
    "game_scorecard",
    "team_roster",
    "event_scroller",
    "important_game_messages"
};

inline constexpr const char* const kScorecardRowElementTypes[] = {
    "player_name",
    "player_role",
    "player_score",
    "player_lives",
    "player_ammo",
    "player_missiles",
    "player_special_points",
    "player_goals",
    "player_assists",
    "player_clears",
    "player_steals",
    "player_zaps",
    "player_medic_hits",
    "player_shots_fired",
    "player_shots_landed",
    "player_accuracy",
    "player_accuracy_string",
    "missiles_fired",
    "missiles_landed",
    "missile_accuracy_string",
    "nukes_activated",
    "nukes_detonated"
};

inline constexpr const char* const kScorecardHeaderElementTypes[] = {
    "user_text",
    "user_image",
    "movie"
};

inline constexpr const char* const kPlayerProfileElementTypes[] = {
    "player_name",
    "player_role",
    "player_score",
    "player_lives",
    "player_ammo",
    "player_missiles",
    "player_special_points",
    "player_profile_picture",
    "team_logo",
    "player_medic_hits",
    "player_shots_fired",
    "player_shots_landed",
    "player_accuracy",
    "player_accuracy_string",
    "missiles_fired",
    "missiles_landed",
    "missile_accuracy_string",
    "nukes_activated",
    "nukes_detonated"
};

inline constexpr const char* const kTemplateTypes[] = {
    "scorecard_row",
    "scorecard_header_row",
    "player_profile"
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_UI_EDITOR_CONSTANTS_HPP_

