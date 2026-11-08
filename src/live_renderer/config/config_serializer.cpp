/**
 * @file config_serializer.cpp
 * @brief Implementation of ConfigSerializer for YAML loading and saving.
 */

#include "live_renderer/config/config_serializer.hpp"
#include <fstream>
#include <yaml-cpp/yaml.h>

namespace live_renderer {

bool ConfigSerializer::LoadGlobalConfig(const std::string& path, GlobalConfig& out_config) {
    try {
        YAML::Node doc = YAML::LoadFile(path);
        if (doc["server"]) {
            auto server = doc["server"];
            if (server["host"]) out_config.host = server["host"].as<std::string>();
            if (server["port"]) out_config.port = server["port"].as<int>();
        }
        if (doc["ui_config_file"]) {
            out_config.ui_config_file = doc["ui_config_file"].as<std::string>();
        }
        if (doc["preferences_file"]) {
            out_config.preferences_file = doc["preferences_file"].as<std::string>();
        }
        return true;
    } catch (...) {
        return false;
    }
}

bool ConfigSerializer::SaveGlobalConfig(const std::string& path, const GlobalConfig& config) {
    try {
        YAML::Emitter out;
        out << YAML::BeginMap;
        out << YAML::Key << "server" << YAML::Value << YAML::BeginMap;
        out << YAML::Key << "host" << YAML::Value << config.host;
        out << YAML::Key << "port" << YAML::Value << config.port;
        out << YAML::EndMap;
        out << YAML::Key << "ui_config_file" << YAML::Value << config.ui_config_file;
        out << YAML::Key << "preferences_file" << YAML::Value << config.preferences_file;
        out << YAML::EndMap;

        std::ofstream fout(path);
        if (!fout.is_open()) return false;
        fout << out.c_str() << "\n";
        return true;
    } catch (...) {
        return false;
    }
}

static void ParseBackgroundConfigNode(
    const YAML::Node& bg, BackgroundConfig& out_bg) {
    out_bg.enabled = true;
    if (bg["enabled"]) {
        out_bg.enabled = bg["enabled"].as<bool>();
    }
    if (bg["color"]) {
        out_bg.color = bg["color"].as<std::string>();
    }
    if (bg["image_file"]) {
        out_bg.image_file = bg["image_file"].as<std::string>();
    }
    if (bg["movie_file"]) {
        out_bg.movie_file = bg["movie_file"].as<std::string>();
    }
    if (bg["fit"]) {
        out_bg.fit = bg["fit"].as<std::string>();
    }
    if (bg["playback_speed"]) {
        out_bg.playback_speed = bg["playback_speed"].as<float>();
    }
    if (bg["tint_team_color"]) {
        out_bg.tint_team_color = bg["tint_team_color"].as<float>();
    }
    if (bg["opacity"]) {
        out_bg.opacity = bg["opacity"].as<float>();
    }
    if (bg["corner_radius"]) {
        out_bg.corner_radius = bg["corner_radius"].as<float>();
    }
}

static void ParseInsetsNode(
    const YAML::Node& insets_node, InsetsConfig& insets) {
    if (!insets_node) return;
    if (insets_node.IsSequence() && insets_node.size() == 4) {
        insets.left = insets_node[0].as<float>();
        insets.right = insets_node[1].as<float>();
        insets.up = insets_node[2].as<float>();
        insets.down = insets_node[3].as<float>();
    } else if (insets_node.IsMap()) {
        if (insets_node["left"]) {
            insets.left = insets_node["left"].as<float>();
        }
        if (insets_node["right"]) {
            insets.right = insets_node["right"].as<float>();
        }
        if (insets_node["up"]) {
            insets.up = insets_node["up"].as<float>();
        } else if (insets_node["top"]) {
            insets.up = insets_node["top"].as<float>();
        }
        if (insets_node["down"]) {
            insets.down = insets_node["down"].as<float>();
        } else if (insets_node["bottom"]) {
            insets.down = insets_node["bottom"].as<float>();
        }
    }
}

static ElementConfig ParseElementNode(const YAML::Node& node) {
    ElementConfig el;
    if (node["type"]) el.type = node["type"].as<std::string>();
    if (node["rect"] && node["rect"].IsSequence() &&
        node["rect"].size() == 4) {
        el.rect = {
            node["rect"][0].as<float>(),
            node["rect"][1].as<float>(),
            node["rect"][2].as<float>(),
            node["rect"][3].as<float>()
        };
    }
    ParseInsetsNode(node["padding"], el.padding);
    ParseInsetsNode(node["margin"], el.margin);
    if (node["z_position"]) el.z_position = node["z_position"].as<int>();
    if (node["text"]) el.text = node["text"].as<std::string>();
    if (node["font"]) el.font = node["font"].as<std::string>();
    if (node["color"]) el.color = node["color"].as<std::string>();
    if (node["font_size"]) el.font_size = node["font_size"].as<float>();
    if (node["alignment"]) el.alignment = node["alignment"].as<std::string>();
    if (node["image_file"]) el.image_file = node["image_file"].as<std::string>();
    if (node["movie_file"]) el.movie_file = node["movie_file"].as<std::string>();
    if (node["fit"]) el.fit = node["fit"].as<std::string>();
    if (node["playback_speed"]) {
        el.playback_speed = node["playback_speed"].as<float>();
    }
    if (node["opacity"]) el.opacity = node["opacity"].as<float>();
    if (node["tilt"]) el.tilt = node["tilt"].as<float>();
    if (node["orientation"]) el.orientation = node["orientation"].as<std::string>();
    if (node["sort_order"]) el.sort_order = node["sort_order"].as<std::string>();
    if (node["add_totals"]) el.add_totals = node["add_totals"].as<bool>();
    if (node["team_index"]) el.team_index = node["team_index"].as<int>();
    if (node["row_template_id"]) el.row_template_id = node["row_template_id"].as<int>();
    if (node["header_template_id"]) el.header_template_id = node["header_template_id"].as<int>();
    if (node["player_profile_template_id"]) {
        el.player_profile_template_id = node["player_profile_template_id"].as<int>();
    }
    if (node["change_animation"]) {
        el.change_animation = node["change_animation"].as<std::string>();
        el.player_change_animation = el.change_animation;
        el.team_change_animation = el.change_animation;
    }
    if (node["animation_duration"]) {
        el.animation_duration = node["animation_duration"].as<float>();
        el.player_animation_duration = el.animation_duration;
        el.team_animation_duration = el.animation_duration;
    }
    if (node["player_change_animation"]) {
        el.player_change_animation =
            node["player_change_animation"].as<std::string>();
    }
    if (node["player_animation_duration"]) {
        el.player_animation_duration =
            node["player_animation_duration"].as<float>();
    }
    if (node["team_change_animation"]) {
        el.team_change_animation =
            node["team_change_animation"].as<std::string>();
    }
    if (node["team_animation_duration"]) {
        el.team_animation_duration =
            node["team_animation_duration"].as<float>();
    }
    if (node["vertical_spacing"]) {
        el.vertical_spacing = node["vertical_spacing"].as<float>();
    }
    if (node["tint_team_color"]) {
        el.tint_team_color = node["tint_team_color"].as<float>();
    }
    if (node["lines"]) {
        el.lines = node["lines"].as<int>();
    }
    if (node["display_time"]) {
        el.display_time = node["display_time"].as<float>();
    }
    if (node["fadeout_time"]) {
        el.fadeout_time = node["fadeout_time"].as<float>();
    }
    if (node["background"] && node["background"].IsMap()) {
        ParseBackgroundConfigNode(node["background"], el.background);
    }
    if (node["team_background"] && node["team_background"].IsMap()) {
        ParseBackgroundConfigNode(node["team_background"], el.team_background);
    }
    return el;
}

static void EmitBackgroundConfigNode(
    YAML::Emitter& out,
    const std::string& key_name,
    const BackgroundConfig& bg) {
    if (!bg.enabled && bg.color.empty() && bg.image_file.empty() &&
        bg.movie_file.empty()) {
        return;
    }
    out << YAML::Key << key_name << YAML::Value << YAML::BeginMap;
    out << YAML::Key << "enabled" << YAML::Value << bg.enabled;
    if (!bg.color.empty()) {
        out << YAML::Key << "color" << YAML::Value << bg.color;
    }
    if (!bg.image_file.empty()) {
        out << YAML::Key << "image_file" << YAML::Value << bg.image_file;
    }
    if (!bg.movie_file.empty()) {
        out << YAML::Key << "movie_file" << YAML::Value << bg.movie_file;
    }
    if (!bg.fit.empty() && bg.fit != "stretch") {
        out << YAML::Key << "fit" << YAML::Value << bg.fit;
    }
    if (bg.playback_speed != 1.0f) {
        out << YAML::Key << "playback_speed" << YAML::Value
            << bg.playback_speed;
    }
    if (bg.tint_team_color > 0.0f) {
        out << YAML::Key << "tint_team_color" << YAML::Value
            << bg.tint_team_color;
    }
    if (bg.opacity != 1.0f) {
        out << YAML::Key << "opacity" << YAML::Value << bg.opacity;
    }
    if (bg.corner_radius > 0.0f) {
        out << YAML::Key << "corner_radius" << YAML::Value
            << bg.corner_radius;
    }
    out << YAML::EndMap;
}

static void EmitInsetsNode(
    YAML::Emitter& out, const char* name, const InsetsConfig& insets) {
    if (insets.IsZero()) return;
    out << YAML::Key << name << YAML::Value << YAML::BeginMap;
    if (insets.left != 0.0f) {
        out << YAML::Key << "left" << YAML::Value << insets.left;
    }
    if (insets.right != 0.0f) {
        out << YAML::Key << "right" << YAML::Value << insets.right;
    }
    if (insets.up != 0.0f) {
        out << YAML::Key << "up" << YAML::Value << insets.up;
    }
    if (insets.down != 0.0f) {
        out << YAML::Key << "down" << YAML::Value << insets.down;
    }
    out << YAML::EndMap;
}

static void EmitElementNode(YAML::Emitter& out, const ElementConfig& el) {
    out << YAML::BeginMap;
    out << YAML::Key << "type" << YAML::Value << el.type;
    out << YAML::Key << "rect" << YAML::Value << YAML::Flow << YAML::BeginSeq
        << el.rect[0] << el.rect[1] << el.rect[2] << el.rect[3] << YAML::EndSeq;
    EmitInsetsNode(out, "padding", el.padding);
    EmitInsetsNode(out, "margin", el.margin);
    if (el.z_position != 0) out << YAML::Key << "z_position" << YAML::Value << el.z_position;
    if (!el.text.empty()) out << YAML::Key << "text" << YAML::Value << el.text;
    if (!el.font.empty() && el.font != "default") {
        out << YAML::Key << "font" << YAML::Value << el.font;
    }
    if (!el.color.empty()) out << YAML::Key << "color" << YAML::Value << el.color;
    out << YAML::Key << "font_size" << YAML::Value << el.font_size;
    out << YAML::Key << "alignment" << YAML::Value << el.alignment;
    if (!el.image_file.empty()) out << YAML::Key << "image_file" << YAML::Value << el.image_file;
    if (!el.movie_file.empty()) out << YAML::Key << "movie_file" << YAML::Value << el.movie_file;
    if (!el.fit.empty() && el.fit != "stretch") {
        out << YAML::Key << "fit" << YAML::Value << el.fit;
    }
    if (el.playback_speed != 1.0f) {
        out << YAML::Key << "playback_speed" << YAML::Value << el.playback_speed;
    }
    if (el.tint_team_color > 0.0f) {
        out << YAML::Key << "tint_team_color" << YAML::Value
            << el.tint_team_color;
    }
    if (el.opacity < 1.0f) out << YAML::Key << "opacity" << YAML::Value << el.opacity;
    if (el.tilt != 10.0f) out << YAML::Key << "tilt" << YAML::Value << el.tilt;
    if (el.type == "game_scorecard" || el.type == "team_scorecard" || el.type == "team_roster") {
        out << YAML::Key << "orientation" << YAML::Value << el.orientation;
        out << YAML::Key << "sort_order" << YAML::Value << el.sort_order;
        out << YAML::Key << "add_totals" << YAML::Value << el.add_totals;
        if (el.team_index >= 0) out << YAML::Key << "team_index" << YAML::Value << el.team_index;
        if (el.row_template_id >= 0) out << YAML::Key << "row_template_id" << YAML::Value << el.row_template_id;
        if (el.header_template_id >= 0) out << YAML::Key << "header_template_id" << YAML::Value << el.header_template_id;
        if (el.player_profile_template_id >= 0) {
            out << YAML::Key << "player_profile_template_id" << YAML::Value << el.player_profile_template_id;
        }
        if (!el.player_change_animation.empty() &&
            el.player_change_animation != "none") {
            out << YAML::Key << "player_change_animation" << YAML::Value
                << el.player_change_animation;
            out << YAML::Key << "player_animation_duration" << YAML::Value
                << el.player_animation_duration;
        } else if (!el.change_animation.empty() &&
                   el.change_animation != "none") {
            out << YAML::Key << "change_animation" << YAML::Value
                << el.change_animation;
            if (el.animation_duration != 0.5f) {
                out << YAML::Key << "animation_duration" << YAML::Value
                    << el.animation_duration;
            }
        }
        if (!el.team_change_animation.empty() &&
            el.team_change_animation != "none") {
            out << YAML::Key << "team_change_animation" << YAML::Value
                << el.team_change_animation;
            out << YAML::Key << "team_animation_duration" << YAML::Value
                << el.team_animation_duration;
        }
    }
    if (el.vertical_spacing != 0.0f) {
        out << YAML::Key << "vertical_spacing"
            << YAML::Value << el.vertical_spacing;
    }
    EmitBackgroundConfigNode(out, "background", el.background);
    EmitBackgroundConfigNode(out, "team_background", el.team_background);
    if (el.type == "important_game_messages" ||
        el.type == "messages_display") {
        out << YAML::Key << "lines" << YAML::Value << el.lines;
        if (el.display_time != 4.0f) {
            out << YAML::Key << "display_time" << YAML::Value
                << el.display_time;
        }
        if (el.fadeout_time != 1.0f) {
            out << YAML::Key << "fadeout_time" << YAML::Value
                << el.fadeout_time;
        }
    }
    out << YAML::EndMap;
}

bool ConfigSerializer::LoadUIConfig(const std::string& path, UIConfig& out_config) {
    try {
        YAML::Node doc = YAML::LoadFile(path);
        out_config.templates.clear();
        out_config.windows.clear();

        if (doc["default_font"]) {
            out_config.default_font = doc["default_font"].as<std::string>();
        } else {
            out_config.default_font = "default";
        }

        if (doc["templates"] && doc["templates"].IsSequence()) {
            for (const auto& tmpl_node : doc["templates"]) {
                TemplateConfig tmpl;
                if (tmpl_node["id"]) tmpl.id = tmpl_node["id"].as<int>();
                if (tmpl_node["name"]) tmpl.name = tmpl_node["name"].as<std::string>();
                if (tmpl_node["type"]) tmpl.type = tmpl_node["type"].as<std::string>();
                if (tmpl_node["size"] && tmpl_node["size"].IsSequence() && tmpl_node["size"].size() == 2) {
                    tmpl.size = {tmpl_node["size"][0].as<float>(), tmpl_node["size"][1].as<float>()};
                }
                if (tmpl_node["elements"] && tmpl_node["elements"].IsSequence()) {
                    for (const auto& el_node : tmpl_node["elements"]) {
                        tmpl.elements.push_back(ParseElementNode(el_node));
                    }
                }
                out_config.templates.push_back(tmpl);
            }
        }

        if (doc["windows"] && doc["windows"].IsSequence()) {
            for (const auto& win_node : doc["windows"]) {
                WindowConfig win;
                if (win_node["id"]) win.id = win_node["id"].as<int>();
                if (win_node["title"]) win.title = win_node["title"].as<std::string>();
                if (win_node["rect"] && win_node["rect"].IsSequence() && win_node["rect"].size() == 4) {
                    win.rect = {
                        win_node["rect"][0].as<int>(),
                        win_node["rect"][1].as<int>(),
                        win_node["rect"][2].as<int>(),
                        win_node["rect"][3].as<int>()
                    };
                }
                if (win_node["monitor_id"]) win.monitor_id = win_node["monitor_id"].as<int>();
                if (win_node["elements"] && win_node["elements"].IsSequence()) {
                    for (const auto& el_node : win_node["elements"]) {
                        win.elements.push_back(ParseElementNode(el_node));
                    }
                }
                out_config.windows.push_back(win);
            }
        }
        return true;
    } catch (...) {
        return false;
    }
}

bool ConfigSerializer::SaveUIConfig(const std::string& path, const UIConfig& config) {
    try {
        YAML::Emitter out;
        out << YAML::BeginMap;

        if (!config.default_font.empty() && config.default_font != "default") {
            out << YAML::Key << "default_font"
                << YAML::Value << config.default_font;
        }

        // Templates
        out << YAML::Key << "templates" << YAML::Value << YAML::BeginSeq;
        for (const auto& tmpl : config.templates) {
            out << YAML::BeginMap;
            out << YAML::Key << "id" << YAML::Value << tmpl.id;
            out << YAML::Key << "name" << YAML::Value << tmpl.name;
            out << YAML::Key << "type" << YAML::Value << tmpl.type;
            out << YAML::Key << "size" << YAML::Value << YAML::Flow << YAML::BeginSeq
                << tmpl.size[0] << tmpl.size[1] << YAML::EndSeq;
            out << YAML::Key << "elements" << YAML::Value << YAML::BeginSeq;
            for (const auto& el : tmpl.elements) {
                EmitElementNode(out, el);
            }
            out << YAML::EndSeq;
            out << YAML::EndMap;
        }
        out << YAML::EndSeq;

        // Windows
        out << YAML::Key << "windows" << YAML::Value << YAML::BeginSeq;
        for (const auto& win : config.windows) {
            out << YAML::BeginMap;
            out << YAML::Key << "id" << YAML::Value << win.id;
            out << YAML::Key << "title" << YAML::Value << win.title;
            out << YAML::Key << "rect" << YAML::Value << YAML::Flow << YAML::BeginSeq
                << win.rect[0] << win.rect[1] << win.rect[2] << win.rect[3] << YAML::EndSeq;
            out << YAML::Key << "monitor_id" << YAML::Value << win.monitor_id;
            out << YAML::Key << "elements" << YAML::Value << YAML::BeginSeq;
            for (const auto& el : win.elements) {
                EmitElementNode(out, el);
            }
            out << YAML::EndSeq;
            out << YAML::EndMap;
        }
        out << YAML::EndSeq;

        out << YAML::EndMap;

        std::ofstream fout(path);
        if (!fout.is_open()) return false;
        fout << out.c_str() << "\n";
        return true;
    } catch (...) {
        return false;
    }
}

static WindowPreference ParseWindowPreference(const YAML::Node& node) {
    WindowPreference pref;
    if (node["id"]) pref.window_id = node["id"].as<int>();
    if (node["window_id"]) pref.window_id = node["window_id"].as<int>();
    if (node["rect"] && node["rect"].IsSequence() && node["rect"].size() == 4) {
        pref.x = node["rect"][0].as<int>();
        pref.y = node["rect"][1].as<int>();
        pref.width = node["rect"][2].as<int>();
        pref.height = node["rect"][3].as<int>();
    }
    if (node["x"]) pref.x = node["x"].as<int>();
    if (node["y"]) pref.y = node["y"].as<int>();
    if (node["width"]) pref.width = node["width"].as<int>();
    if (node["height"]) pref.height = node["height"].as<int>();
    if (node["display_index"]) pref.display_index = node["display_index"].as<int>();
    if (node["monitor_id"]) pref.display_index = node["monitor_id"].as<int>();
    if (node["display_name"]) pref.display_name = node["display_name"].as<std::string>();
    return pref;
}

static void EmitWindowPreference(
    YAML::Emitter& out,
    const WindowPreference& pref,
    bool include_id = true) {
    out << YAML::BeginMap;
    if (include_id) {
        out << YAML::Key << "id" << YAML::Value << pref.window_id;
    }
    out << YAML::Key << "x" << YAML::Value << pref.x;
    out << YAML::Key << "y" << YAML::Value << pref.y;
    out << YAML::Key << "width" << YAML::Value << pref.width;
    out << YAML::Key << "height" << YAML::Value << pref.height;
    out << YAML::Key << "display_index" << YAML::Value << pref.display_index;
    if (!pref.display_name.empty()) {
        out << YAML::Key << "display_name" << YAML::Value << pref.display_name;
    }
    out << YAML::EndMap;
}

bool ConfigSerializer::LoadPreferences(
    const std::string& path,
    LocalPreferences& out_preferences) {
    try {
        YAML::Node doc = YAML::LoadFile(path);
        out_preferences.windows.clear();
        out_preferences.main_control_window.reset();

        if (doc["main_control_window"]) {
            out_preferences.main_control_window = ParseWindowPreference(
                doc["main_control_window"]);
        }

        if (doc["windows"] && doc["windows"].IsSequence()) {
            for (const auto& win_node : doc["windows"]) {
                out_preferences.windows.push_back(
                    ParseWindowPreference(win_node));
            }
        }
        return true;
    } catch (...) {
        return false;
    }
}

bool ConfigSerializer::SavePreferences(
    const std::string& path,
    const LocalPreferences& preferences) {
    try {
        YAML::Emitter out;
        out << YAML::BeginMap;

        if (preferences.main_control_window.has_value()) {
            out << YAML::Key << "main_control_window" << YAML::Value;
            EmitWindowPreference(out, *preferences.main_control_window, false);
        }

        out << YAML::Key << "windows" << YAML::Value << YAML::BeginSeq;
        for (const auto& win : preferences.windows) {
            EmitWindowPreference(out, win, true);
        }
        out << YAML::EndSeq;

        out << YAML::EndMap;

        std::ofstream fout(path);
        if (!fout.is_open()) return false;
        fout << out.c_str() << "\n";
        return true;
    } catch (...) {
        return false;
    }
}

}  // namespace live_renderer
