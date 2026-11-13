#include "live_renderer/render/rich_text_layout.hpp"
#include <regex>

namespace live_renderer {

std::string RichTextLayout::SubstitutePlaceholders(
    std::string_view raw_text,
    const GameStateSnapshot& state) {
    std::string result(raw_text);

    auto replace_all = [](std::string& str, const std::string& from, const std::string& to) {
        size_t start_pos = 0;
        while ((start_pos = str.find(from, start_pos)) != std::string::npos) {
            str.replace(start_pos, from.length(), to);
            start_pos += to.length();
        }
    };

    replace_all(result, "{game_type}", state.game_type);
    replace_all(result, "{center}", state.center_name.empty() ? state.center_id : state.center_name);
    replace_all(result, "{competition_name}", state.competition_name);
    replace_all(result, "{competition_team_1_name}", state.competition_team_1_name);
    replace_all(result, "{competition_team_2_name}", state.competition_team_2_name);
    replace_all(result, "{next_scheduled_game_team_1_name}", state.next_scheduled_game_team_1_name);
    replace_all(result, "{next_scheduled_game_team_2_name}", state.next_scheduled_game_team_2_name);

    return result;
}

std::vector<TextRun> RichTextLayout::ParseMarkup(
    std::string_view text,
    const std::string& default_color) {
    std::vector<TextRun> runs;
    if (text.empty()) return runs;

    // Pattern matches <font color="...">(.*?)</font> or [img:...]
    // We parse token by token
    size_t i = 0;
    std::string current_color = default_color;

    while (i < text.size()) {
        if (text[i] == '<' && text.substr(i, 12) == "<font color=") {
            size_t tag_end = text.find('>', i);
            if (tag_end != std::string_view::npos) {
                // Extract color value between quotes
                size_t q1 = text.find('"', i);
                size_t q2 = (q1 != std::string_view::npos) ? text.find('"', q1 + 1) : std::string_view::npos;
                std::string color = default_color;
                if (q1 != std::string_view::npos && q2 != std::string_view::npos && q2 <= tag_end) {
                    color = std::string(text.substr(q1 + 1, q2 - q1 - 1));
                }

                size_t close_tag = text.find("</font>", tag_end + 1);
                if (close_tag != std::string_view::npos) {
                    std::string_view inner_text = text.substr(tag_end + 1, close_tag - tag_end - 1);
                    if (!inner_text.empty()) {
                        runs.push_back({std::string(inner_text), color, false, ""});
                    }
                    i = close_tag + 7; // Length of "</font>"
                    continue;
                }
            }
        } else if (text[i] == '[' && text.substr(i, 5) == "[img:") {
            size_t bracket_end = text.find(']', i);
            if (bracket_end != std::string_view::npos) {
                std::string asset = std::string(text.substr(i + 5, bracket_end - i - 5));
                runs.push_back({"", "", true, asset});
                i = bracket_end + 1;
                continue;
            }
        }

        // Plain text segment up to the next tag or end
        size_t next_font = text.find("<font", i);
        size_t next_img = text.find("[img:", i);
        size_t next_tag = std::min(next_font, next_img);

        size_t len = (next_tag == std::string_view::npos) ? text.size() - i : next_tag - i;
        if (len > 0) {
            runs.push_back({std::string(text.substr(i, len)), default_color, false, ""});
            i += len;
        } else {
            // Unmatched tag, consume one char
            runs.push_back({std::string(1, text[i]), default_color, false, ""});
            i++;
        }
    }

    return runs;
}

}  // namespace live_renderer

