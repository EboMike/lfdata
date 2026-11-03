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
        out << YAML::EndMap;

        std::ofstream fout(path);
        if (!fout.is_open()) return false;
        fout << out.c_str() << "\n";
        return true;
    } catch (...) {
        return false;
    }
}

static ElementConfig ParseElementNode(const YAML::Node& node) {
    ElementConfig el;
    if (node["type"]) el.type = node["type"].as<std::string>();
    if (node["rect"] && node["rect"].IsSequence() && node["rect"].size() == 4) {
        el.rect = {
            node["rect"][0].as<float>(),
            node["rect"][1].as<float>(),
            node["rect"][2].as<float>(),
            node["rect"][3].as<float>()
        };
    }
    if (node["text"]) el.text = node["text"].as<std::string>();
    if (node["color"]) el.color = node["color"].as<std::string>();
    if (node["font_size"]) el.font_size = node["font_size"].as<float>();
    if (node["alignment"]) el.alignment = node["alignment"].as<std::string>();
    if (node["image_file"]) el.image_file = node["image_file"].as<std::string>();
    if (node["opacity"]) el.opacity = node["opacity"].as<float>();
    if (node["tilt"]) el.tilt = node["tilt"].as<float>();
    if (node["orientation"]) el.orientation = node["orientation"].as<std::string>();
    if (node["sort_order"]) el.sort_order = node["sort_order"].as<std::string>();
    if (node["add_totals"]) el.add_totals = node["add_totals"].as<bool>();
    if (node["team_index"]) el.team_index = node["team_index"].as<int>();
    if (node["row_template_id"]) el.row_template_id = node["row_template_id"].as<int>();
    if (node["header_template_id"]) el.header_template_id = node["header_template_id"].as<int>();
    if (node["player_profile_template_id"]) el.player_profile_template_id = node["player_profile_template_id"].as<int>();
    return el;
}

static void EmitElementNode(YAML::Emitter& out, const ElementConfig& el) {
    out << YAML::BeginMap;
    out << YAML::Key << "type" << YAML::Value << el.type;
    out << YAML::Key << "rect" << YAML::Value << YAML::Flow << YAML::BeginSeq
        << el.rect[0] << el.rect[1] << el.rect[2] << el.rect[3] << YAML::EndSeq;
    if (!el.text.empty()) out << YAML::Key << "text" << YAML::Value << el.text;
    if (!el.color.empty()) out << YAML::Key << "color" << YAML::Value << el.color;
    out << YAML::Key << "font_size" << YAML::Value << el.font_size;
    out << YAML::Key << "alignment" << YAML::Value << el.alignment;
    if (!el.image_file.empty()) out << YAML::Key << "image_file" << YAML::Value << el.image_file;
    if (el.opacity < 1.0f) out << YAML::Key << "opacity" << YAML::Value << el.opacity;
    if (el.tilt != 10.0f) out << YAML::Key << "tilt" << YAML::Value << el.tilt;
    if (el.type == "game_scorecard" || el.type == "team_scorecard" || el.type == "team_roster") {
        out << YAML::Key << "orientation" << YAML::Value << el.orientation;
        out << YAML::Key << "sort_order" << YAML::Value << el.sort_order;
        out << YAML::Key << "add_totals" << YAML::Value << el.add_totals;
        if (el.team_index >= 0) out << YAML::Key << "team_index" << YAML::Value << el.team_index;
        if (el.row_template_id >= 0) out << YAML::Key << "row_template_id" << YAML::Value << el.row_template_id;
        if (el.header_template_id >= 0) out << YAML::Key << "header_template_id" << YAML::Value << el.header_template_id;
        if (el.player_profile_template_id >= 0) out << YAML::Key << "player_profile_template_id" << YAML::Value << el.player_profile_template_id;
    }
    out << YAML::EndMap;
}

bool ConfigSerializer::LoadUIConfig(const std::string& path, UIConfig& out_config) {
    try {
        YAML::Node doc = YAML::LoadFile(path);
        out_config.templates.clear();
        out_config.windows.clear();

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

}  // namespace live_renderer

