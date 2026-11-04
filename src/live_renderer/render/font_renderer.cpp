/**
 * @file font_renderer.cpp
 * @brief FontRenderer implementation with TrueType font baking and rendering.
 */

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#define STB_TRUETYPE_IMPLEMENTATION
#include "live_renderer/render/font_renderer.hpp"

#include <SDL_opengl.h>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <vector>

namespace live_renderer {

namespace {

// Standard 8x8 monochrome bitmap font glyphs for ASCII 32 (' ') to 126 ('~')
const uint8_t kFont8x8[95][8] = {
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}, // 32 ' '
    {0x18,0x3c,0x3c,0x18,0x18,0x00,0x18,0x00}, // 33 '!'
    {0x66,0x66,0x24,0x00,0x00,0x00,0x00,0x00}, // 34 '"'
    {0x6c,0x6c,0xfe,0x6c,0xfe,0x6c,0x6c,0x00}, // 35 '#'
    {0x18,0x3e,0x60,0x3c,0x06,0x7c,0x18,0x00}, // 36 '$'
    {0x00,0x63,0x66,0x0c,0x18,0x33,0x63,0x00}, // 37 '%'
    {0x38,0x6c,0x38,0x76,0xdc,0xcc,0x76,0x00}, // 38 '&'
    {0x30,0x30,0x10,0x20,0x00,0x00,0x00,0x00}, // 39 '\''
    {0x0c,0x18,0x30,0x30,0x30,0x18,0x0c,0x00}, // 40 '('
    {0x30,0x18,0x0c,0x0c,0x0c,0x18,0x30,0x00}, // 41 ')'
    {0x00,0x66,0x3c,0xff,0x3c,0x66,0x00,0x00}, // 42 '*'
    {0x00,0x18,0x18,0x7e,0x18,0x18,0x00,0x00}, // 43 '+'
    {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x30}, // 44 ','
    {0x00,0x00,0x00,0x7e,0x00,0x00,0x00,0x00}, // 45 '-'
    {0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00}, // 46 '.'
    {0x03,0x06,0x0c,0x18,0x30,0x60,0x40,0x00}, // 47 '/'
    {0x3c,0x66,0x6e,0x76,0x66,0x66,0x3c,0x00}, // 48 '0'
    {0x18,0x38,0x18,0x18,0x18,0x18,0x7e,0x00}, // 49 '1'
    {0x3c,0x66,0x06,0x0c,0x18,0x30,0x7e,0x00}, // 50 '2'
    {0x3c,0x66,0x06,0x1c,0x06,0x66,0x3c,0x00}, // 51 '3'
    {0x0c,0x1c,0x34,0x64,0x7e,0x04,0x0c,0x00}, // 52 '4'
    {0x7e,0x60,0x7c,0x06,0x06,0x66,0x3c,0x00}, // 53 '5'
    {0x1c,0x30,0x60,0x7c,0x66,0x66,0x3c,0x00}, // 54 '6'
    {0x7e,0x06,0x0c,0x18,0x30,0x30,0x30,0x00}, // 55 '7'
    {0x3c,0x66,0x66,0x3c,0x66,0x66,0x3c,0x00}, // 56 '8'
    {0x3c,0x66,0x66,0x3e,0x06,0x0c,0x38,0x00}, // 57 '9'
    {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x00}, // 58 ':'
    {0x00,0x18,0x18,0x00,0x00,0x18,0x18,0x30}, // 59 ';'
    {0x06,0x0c,0x18,0x30,0x18,0x0c,0x06,0x00}, // 60 '<'
    {0x00,0x00,0x7e,0x00,0x7e,0x00,0x00,0x00}, // 61 '='
    {0x30,0x18,0x0c,0x06,0x0c,0x18,0x30,0x00}, // 62 '>'
    {0x3c,0x66,0x06,0x0c,0x18,0x00,0x18,0x00}, // 63 '?'
    {0x3c,0x66,0x6e,0x6a,0x6e,0x60,0x3c,0x00}, // 64 '@'
    {0x18,0x3c,0x66,0x66,0x7e,0x66,0x66,0x00}, // 65 'A'
    {0x7c,0x66,0x66,0x7c,0x66,0x66,0x7c,0x00}, // 66 'B'
    {0x3c,0x66,0x60,0x60,0x60,0x66,0x3c,0x00}, // 67 'C'
    {0x78,0x6c,0x66,0x66,0x66,0x6c,0x78,0x00}, // 68 'D'
    {0x7e,0x60,0x60,0x7c,0x60,0x60,0x7e,0x00}, // 69 'E'
    {0x7e,0x60,0x60,0x7c,0x60,0x60,0x60,0x00}, // 70 'F'
    {0x3c,0x66,0x60,0x6e,0x66,0x66,0x3e,0x00}, // 71 'G'
    {0x66,0x66,0x66,0x7e,0x66,0x66,0x66,0x00}, // 72 'H'
    {0x3c,0x18,0x18,0x18,0x18,0x18,0x3c,0x00}, // 73 'I'
    {0x0e,0x06,0x06,0x06,0x06,0x66,0x3c,0x00}, // 74 'J'
    {0x66,0x6c,0x78,0x70,0x78,0x6c,0x66,0x00}, // 75 'K'
    {0x60,0x60,0x60,0x60,0x60,0x60,0x7e,0x00}, // 76 'L'
    {0x63,0x77,0x7f,0x6b,0x63,0x63,0x63,0x00}, // 77 'M'
    {0x66,0x76,0x7e,0x7e,0x6e,0x66,0x66,0x00}, // 78 'N'
    {0x3c,0x66,0x66,0x66,0x66,0x66,0x3c,0x00}, // 79 'O'
    {0x7c,0x66,0x66,0x7c,0x60,0x60,0x60,0x00}, // 80 'P'
    {0x3c,0x66,0x66,0x66,0x6a,0x6c,0x36,0x00}, // 81 'Q'
    {0x7c,0x66,0x66,0x7c,0x6c,0x66,0x66,0x00}, // 82 'R'
    {0x3c,0x66,0x60,0x3c,0x06,0x66,0x3c,0x00}, // 83 'S'
    {0x7e,0x18,0x18,0x18,0x18,0x18,0x18,0x00}, // 84 'T'
    {0x66,0x66,0x66,0x66,0x66,0x66,0x3c,0x00}, // 85 'U'
    {0x66,0x66,0x66,0x66,0x66,0x3c,0x18,0x00}, // 86 'V'
    {0x63,0x63,0x63,0x6b,0x7f,0x77,0x63,0x00}, // 87 'W'
    {0x66,0x66,0x3c,0x18,0x3c,0x66,0x66,0x00}, // 88 'X'
    {0x66,0x66,0x66,0x3c,0x18,0x18,0x18,0x00}, // 89 'Y'
    {0x7e,0x06,0x0c,0x18,0x30,0x60,0x7e,0x00}, // 90 'Z'
    {0x3c,0x30,0x30,0x30,0x30,0x30,0x3c,0x00}, // 91 '['
    {0x60,0x30,0x18,0x0c,0x06,0x03,0x01,0x00}, // 92 '\\'
    {0x3c,0x0c,0x0c,0x0c,0x0c,0x0c,0x3c,0x00}, // 93 ']'
    {0x08,0x1c,0x36,0x63,0x00,0x00,0x00,0x00}, // 94 '^'
    {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xff}, // 95 '_'
    {0x18,0x18,0x0c,0x00,0x00,0x00,0x00,0x00}, // 96 '`'
    {0x00,0x00,0x3c,0x06,0x3e,0x66,0x3e,0x00}, // 97 'a'
    {0x60,0x60,0x7c,0x66,0x66,0x66,0x7c,0x00}, // 98 'b'
    {0x00,0x00,0x3c,0x66,0x60,0x66,0x3c,0x00}, // 99 'c'
    {0x06,0x06,0x3e,0x66,0x66,0x66,0x3e,0x00}, // 100 'd'
    {0x00,0x00,0x3c,0x66,0x7e,0x60,0x3c,0x00}, // 101 'e'
    {0x1c,0x30,0x78,0x30,0x30,0x30,0x30,0x00}, // 102 'f'
    {0x00,0x00,0x3e,0x66,0x66,0x3e,0x06,0x3c}, // 103 'g'
    {0x60,0x60,0x7c,0x66,0x66,0x66,0x66,0x00}, // 104 'h'
    {0x18,0x00,0x38,0x18,0x18,0x18,0x3c,0x00}, // 105 'i'
    {0x06,0x00,0x0e,0x06,0x06,0x66,0x3c,0x00}, // 106 'j'
    {0x60,0x60,0x66,0x6c,0x78,0x6c,0x66,0x00}, // 107 'k'
    {0x38,0x18,0x18,0x18,0x18,0x18,0x3c,0x00}, // 108 'l'
    {0x00,0x00,0x66,0x7f,0x7f,0x6b,0x63,0x00}, // 109 'm'
    {0x00,0x00,0x7c,0x66,0x66,0x66,0x66,0x00}, // 110 'n'
    {0x00,0x00,0x3c,0x66,0x66,0x66,0x3c,0x00}, // 111 'o'
    {0x00,0x00,0x7c,0x66,0x66,0x7c,0x60,0x60}, // 112 'p'
    {0x00,0x00,0x3e,0x66,0x66,0x3e,0x06,0x06}, // 113 'q'
    {0x00,0x00,0x7c,0x66,0x60,0x60,0x60,0x00}, // 114 'r'
    {0x00,0x00,0x3e,0x60,0x3c,0x06,0x7c,0x00}, // 115 's'
    {0x18,0x18,0x7e,0x18,0x18,0x18,0x0e,0x00}, // 116 't'
    {0x00,0x00,0x66,0x66,0x66,0x66,0x3e,0x00}, // 117 'u'
    {0x00,0x00,0x66,0x66,0x66,0x3c,0x18,0x00}, // 118 'v'
    {0x00,0x00,0x63,0x6b,0x7f,0x77,0x36,0x00}, // 119 'w'
    {0x00,0x00,0x66,0x3c,0x18,0x3c,0x66,0x00}, // 120 'x'
    {0x00,0x00,0x66,0x66,0x66,0x3e,0x06,0x3c}, // 121 'y'
    {0x00,0x00,0x7e,0x0c,0x18,0x30,0x7e,0x00}, // 122 'z'
    {0x0e,0x18,0x18,0x70,0x18,0x18,0x0e,0x00}, // 123 '{'
    {0x18,0x18,0x18,0x00,0x18,0x18,0x18,0x00}, // 124 '|'
    {0x70,0x18,0x18,0x0e,0x18,0x18,0x70,0x00}, // 125 '}'
    {0x36,0x5c,0x00,0x00,0x00,0x00,0x00,0x00}  // 126 '~'
};

void ParseHex(const std::string& hex, float rgba[4]) {
    rgba[0] = 1.0f; rgba[1] = 1.0f; rgba[2] = 1.0f; rgba[3] = 1.0f;
    if (hex.size() >= 7 && hex[0] == '#') {
        try {
            int r = std::stoi(hex.substr(1, 2), nullptr, 16);
            int g = std::stoi(hex.substr(3, 2), nullptr, 16);
            int b = std::stoi(hex.substr(5, 2), nullptr, 16);
            rgba[0] = r / 255.0f;
            rgba[1] = g / 255.0f;
            rgba[2] = b / 255.0f;
            if (hex.size() >= 9) {
                int a = std::stoi(hex.substr(7, 2), nullptr, 16);
                rgba[3] = a / 255.0f;
            }
        } catch (...) {}
    }
}

#if defined(_WIN32)
std::vector<uint8_t> LoadFontDataViaGDI(const std::string& font_name) {
    std::vector<uint8_t> buffer;
    HDC hdc = CreateCompatibleDC(nullptr);
    if (!hdc) return buffer;

    HFONT hFont = CreateFontA(
        0, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
        DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE,
        font_name.c_str());
    if (hFont) {
        HGDIOBJ old = SelectObject(hdc, hFont);
        DWORD size = GetFontData(hdc, 0, 0, nullptr, 0);
        if (size != GDI_ERROR && size > 0) {
            buffer.resize(size);
            GetFontData(hdc, 0, 0, buffer.data(), size);
        }
        SelectObject(hdc, old);
        DeleteObject(hFont);
    }
    DeleteDC(hdc);
    return buffer;
}
#endif

}  // namespace

std::string FontRenderer::default_font_ = "default";
std::unordered_map<std::string, BakedGlyphFont> FontRenderer::font_cache_;
std::mutex FontRenderer::font_mutex_;
int FontRenderer::instance_count_ = 0;

FontRenderer::FontRenderer() {
    std::lock_guard<std::mutex> lock(font_mutex_);
    ++instance_count_;
}

FontRenderer::~FontRenderer() {
    if (fallback_texture_id_ != 0) {
        glDeleteTextures(1, &fallback_texture_id_);
        fallback_texture_id_ = 0;
    }
    std::lock_guard<std::mutex> lock(font_mutex_);
    if (--instance_count_ <= 0) {
        instance_count_ = 0;
        for (auto& [name, font] : font_cache_) {
            if (font.texture_id != 0) {
                glDeleteTextures(1, &font.texture_id);
                font.texture_id = 0;
            }
        }
        font_cache_.clear();
    }
}

void FontRenderer::SetDefaultFont(const std::string& font_name) {
    std::lock_guard<std::mutex> lock(font_mutex_);
    default_font_ = font_name;
}

const std::string& FontRenderer::GetDefaultFont() {
    std::lock_guard<std::mutex> lock(font_mutex_);
    return default_font_;
}

std::string FontRenderer::ResolveFontPath(const std::string& font_name) {
    if (font_name.empty() || font_name == "default") {
        return "";
    }

    namespace fs = std::filesystem;

    if (fs::exists(font_name)) {
        return font_name;
    }

    const std::vector<std::string> font_dirs = {
        "fonts/",
        "../fonts/",
        "../../fonts/"
    };

    for (const auto& dir : font_dirs) {
        if (fs::exists(dir + font_name)) {
            return dir + font_name;
        }
        if (fs::exists(dir + font_name + ".ttf")) {
            return dir + font_name + ".ttf";
        }
        if (fs::exists(dir + font_name + ".otf")) {
            return dir + font_name + ".otf";
        }
    }

#if defined(_WIN32)
    char win_dir[MAX_PATH]{};
    if (GetWindowsDirectoryA(win_dir, MAX_PATH) > 0) {
        std::string win_fonts = std::string(win_dir) + "\\Fonts\\";
        if (fs::exists(win_fonts + font_name)) {
            return win_fonts + font_name;
        }
        if (fs::exists(win_fonts + font_name + ".ttf")) {
            return win_fonts + font_name + ".ttf";
        }
        if (fs::exists(win_fonts + font_name + ".otf")) {
            return win_fonts + font_name + ".otf";
        }

        HKEY h_key = nullptr;
        if (RegOpenKeyExA(
                HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
                0, KEY_READ, &h_key) == ERROR_SUCCESS) {
            char val_name[512]{};
            BYTE val_data[512]{};
            DWORD val_name_len = sizeof(val_name);
            DWORD val_data_len = sizeof(val_data);
            DWORD type = 0;
            DWORD index = 0;

            std::string target_name = font_name;
            std::transform(
                target_name.begin(), target_name.end(),
                target_name.begin(), ::tolower);

            std::string matched_file;
            while (RegEnumValueA(
                       h_key, index, val_name, &val_name_len,
                       nullptr, &type, val_data,
                       &val_data_len) == ERROR_SUCCESS) {
                std::string entry_lower(val_name);
                std::transform(
                    entry_lower.begin(), entry_lower.end(),
                    entry_lower.begin(), ::tolower);

                if (entry_lower == target_name ||
                    (entry_lower.rfind(target_name, 0) == 0 &&
                     (entry_lower.size() == target_name.size() ||
                      entry_lower[target_name.size()] == ' ' ||
                      entry_lower[target_name.size()] == '(' ||
                      entry_lower[target_name.size()] == '&'))) {
                    matched_file = reinterpret_cast<char*>(val_data);
                    break;
                }

                index++;
                val_name_len = sizeof(val_name);
                val_data_len = sizeof(val_data);
            }
            RegCloseKey(h_key);

            if (!matched_file.empty()) {
                if (fs::exists(matched_file)) {
                    return matched_file;
                }
                std::string full_path = win_fonts + matched_file;
                if (fs::exists(full_path)) {
                    return full_path;
                }
            }
        }
    }
#endif

    return "";
}

BakedGlyphFont* FontRenderer::GetOrLoadFontLocked(
    const std::string& font_name) {
    std::string effective_name =
        (font_name.empty() || font_name == "default")
            ? default_font_
            : font_name;

    if (effective_name.empty() || effective_name == "default") {
        return nullptr;
    }

    auto it = font_cache_.find(effective_name);
    if (it != font_cache_.end()) {
        return it->second.is_valid ? &it->second : nullptr;
    }

    std::vector<uint8_t> buffer;
    std::string resolved_path = ResolveFontPath(effective_name);
    if (!resolved_path.empty()) {
        std::ifstream file(resolved_path, std::ios::binary | std::ios::ate);
        if (file.is_open()) {
            std::streamsize size = file.tellg();
            if (size > 0) {
                file.seekg(0, std::ios::beg);
                buffer.resize(static_cast<size_t>(size));
                file.read(
                    reinterpret_cast<char*>(buffer.data()), size);
            }
        }
    }

#if defined(_WIN32)
    if (buffer.empty()) {
        buffer = LoadFontDataViaGDI(effective_name);
    }
#endif

    if (buffer.empty()) {
        BakedGlyphFont invalid_font;
        invalid_font.is_valid = false;
        font_cache_[effective_name] = invalid_font;
        return nullptr;
    }

    stbtt_fontinfo info{};
    int offset = stbtt_GetFontOffsetForIndex(buffer.data(), 0);
    if (offset < 0) offset = 0;
    if (!stbtt_InitFont(&info, buffer.data(), offset)) {
        BakedGlyphFont invalid_font;
        invalid_font.is_valid = false;
        font_cache_[effective_name] = invalid_font;
        return nullptr;
    }

    BakedGlyphFont font;
    font.baked_size = 64.0f;
    font.tex_width = 1024;
    font.tex_height = 1024;
    font.cdata.resize(96);

    int ascent = 0;
    int descent = 0;
    int line_gap = 0;
    stbtt_GetFontVMetrics(&info, &ascent, &descent, &line_gap);
    float scale = stbtt_ScaleForPixelHeight(&info, font.baked_size);
    font.ascent = static_cast<float>(ascent) * scale;
    font.descent = static_cast<float>(descent) * scale;
    font.line_gap = static_cast<float>(line_gap) * scale;

    std::vector<uint8_t> mono_bitmap(font.tex_width * font.tex_height, 0);
    int res = stbtt_BakeFontBitmap(
        buffer.data(), offset, font.baked_size,
        mono_bitmap.data(), font.tex_width, font.tex_height,
        32, 96, font.cdata.data());

    if (res <= 0) {
        BakedGlyphFont invalid_font;
        invalid_font.is_valid = false;
        font_cache_[effective_name] = invalid_font;
        return nullptr;
    }

    font.rgba_pixels.resize(font.tex_width * font.tex_height * 4, 255);
    for (size_t i = 0; i < mono_bitmap.size(); ++i) {
        font.rgba_pixels[i * 4 + 0] = 255;
        font.rgba_pixels[i * 4 + 1] = 255;
        font.rgba_pixels[i * 4 + 2] = 255;
        font.rgba_pixels[i * 4 + 3] = mono_bitmap[i];
    }

    font.is_valid = true;
    font_cache_[effective_name] = std::move(font);
    return &font_cache_[effective_name];
}

void FontRenderer::EnsureTextureUploaded(BakedGlyphFont& font) {
    if (font.texture_id == 0 && !font.rgba_pixels.empty()) {
        glGenTextures(1, &font.texture_id);
        glBindTexture(GL_TEXTURE_2D, font.texture_id);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            font.tex_width, font.tex_height, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, font.rgba_pixels.data());
        glBindTexture(GL_TEXTURE_2D, 0);
    }
}

void FontRenderer::EnsureFallbackTextureInitialized() {
    if (fallback_initialized_) return;

    constexpr int kTexWidth = 128;
    constexpr int kTexHeight = 128;
    std::vector<uint8_t> pixels(kTexWidth * kTexHeight * 4, 0);

    for (int char_idx = 0; char_idx < 95; ++char_idx) {
        int cell_x = (char_idx % 16) * 8;
        int cell_y = (char_idx / 16) * 8;

        for (int row = 0; row < 8; ++row) {
            uint8_t bits = kFont8x8[char_idx][row];
            for (int col = 0; col < 8; ++col) {
                if ((bits >> (7 - col)) & 1) {
                    int px = cell_x + col;
                    int py = cell_y + row;
                    int offset = (py * kTexWidth + px) * 4;
                    pixels[offset + 0] = 255;
                    pixels[offset + 1] = 255;
                    pixels[offset + 2] = 255;
                    pixels[offset + 3] = 255;
                }
            }
        }
    }

    glGenTextures(1, &fallback_texture_id_);
    glBindTexture(GL_TEXTURE_2D, fallback_texture_id_);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);

    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA,
        kTexWidth, kTexHeight, 0,
        GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());

    glBindTexture(GL_TEXTURE_2D, 0);
    fallback_initialized_ = true;
}

float FontRenderer::MeasureText(
    const std::string& text,
    const std::string& font_name,
    float font_size_px) {
    if (text.empty() || font_size_px <= 0.0f) return 0.0f;

    std::lock_guard<std::mutex> lock(font_mutex_);
    std::string font_to_use =
        (font_name.empty() || font_name == "default")
            ? default_font_
            : font_name;

    BakedGlyphFont* font = GetOrLoadFontLocked(font_to_use);
    if (font != nullptr && font->is_valid) {
        float scale = font_size_px / font->baked_size;
        float total_w = 0.0f;
        for (char c : text) {
            if (c >= 32 && c <= 126) {
                total_w += font->cdata[c - 32].xadvance * scale;
            } else {
                total_w += font->cdata[' ' - 32].xadvance * scale;
            }
        }
        return total_w;
    }

    return static_cast<float>(text.size()) * (font_size_px * 0.60f);
}

float FontRenderer::MeasureTextWidth(
    const std::string& text,
    const std::string& font_name,
    float font_size_px) {
    return MeasureText(text, font_name, font_size_px);
}

void FontRenderer::DrawStringQuadsTTF(
    const BakedGlyphFont& font,
    const std::string& text,
    float x,
    float y,
    float font_size_px,
    const float color_rgba[4],
    float tilt_deg,
    const std::array<float, 4>& container_rect) {
    EnsureTextureUploaded(const_cast<BakedGlyphFont&>(font));
    if (font.texture_id == 0) {
        DrawStringQuadsFallback(
            text, x, y, font_size_px, color_rgba, tilt_deg, container_rect);
        return;
    }

    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, font.texture_id);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);

    const float scale = font_size_px / font.baked_size;
    const float baseline_y = y + (font.ascent * scale);

    const bool has_tilt = (
        tilt_deg != 0.0f &&
        container_rect[2] > 0.0f &&
        container_rect[3] > 0.0f);

    const float cx0 = container_rect[0];
    const float cy0 = container_rect[1];
    const float cw  = container_rect[2];
    const float ch  = container_rect[3];
    const float cx_center = cx0 + cw * 0.5f;

    constexpr float kDegToRad = 3.14159265358979323846f / 180.0f;
    float dx = 0.0f;
    if (has_tilt) {
        dx = ch * std::tan(tilt_deg * kDegToRad);
        dx = std::clamp(dx, -cw * 0.45f, cw * 0.45f);
    }

    auto TransformVertex = [&](float vx, float vy) -> std::pair<float, float> {
        if (!has_tilt) return {vx, vy};
        float t = std::clamp((vy - cy0) / ch, 0.0f, 1.0f);
        float s = 1.0f - (1.0f - t) * (2.0f * dx / cw);
        float nx = cx_center + (vx - cx_center) * s;
        float ny = (cy0 + ch) - ((cy0 + ch) - vy) * s;
        return {nx, ny};
    };

    auto GetAlphaScale = [&](float vy) -> float {
        if (!has_tilt) return 1.0f;
        float t = (vy - cy0) / ch;
        if (t < 0.25f) {
            return std::clamp(t / 0.25f, 0.0f, 1.0f);
        }
        return 1.0f;
    };

    glBegin(GL_QUADS);
    float cur_x = x;
    const float ipw = 1.0f / font.tex_width;
    const float iph = 1.0f / font.tex_height;

    for (char c : text) {
        if (c < 32 || c > 126) c = ' ';
        int char_idx = c - 32;
        const auto& b = font.cdata[char_idx];

        float glyph_w = static_cast<float>(b.x1 - b.x0) * scale;
        float glyph_h = static_cast<float>(b.y1 - b.y0) * scale;

        float qx0 = cur_x + b.xoff * scale;
        float qy0 = baseline_y + b.yoff * scale;
        float qx1 = qx0 + glyph_w;
        float qy1 = qy0 + glyph_h;

        float u0 = b.x0 * ipw;
        float v0 = b.y0 * iph;
        float u1 = b.x1 * ipw;
        float v1 = b.y1 * iph;

        auto [x0, y0] = TransformVertex(qx0, qy0);
        auto [x1, y1] = TransformVertex(qx1, qy0);
        auto [x2, y2] = TransformVertex(qx1, qy1);
        auto [x3, y3] = TransformVertex(qx0, qy1);

        const float alpha_top = color_rgba[3] * GetAlphaScale(qy0);
        const float alpha_bot = color_rgba[3] * GetAlphaScale(qy1);

        glColor4f(color_rgba[0], color_rgba[1], color_rgba[2], alpha_top);
        glTexCoord2f(u0, v0); glVertex2f(x0, y0);
        glTexCoord2f(u1, v0); glVertex2f(x1, y1);

        glColor4f(color_rgba[0], color_rgba[1], color_rgba[2], alpha_bot);
        glTexCoord2f(u1, v1); glVertex2f(x2, y2);
        glTexCoord2f(u0, v1); glVertex2f(x3, y3);

        cur_x += b.xadvance * scale;
    }
    glEnd();

    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_TEXTURE_2D);
}

void FontRenderer::DrawStringQuadsFallback(
    const std::string& text,
    float x,
    float y,
    float font_size_px,
    const float color_rgba[4],
    float tilt_deg,
    const std::array<float, 4>& container_rect) {
    EnsureFallbackTextureInitialized();

    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, fallback_texture_id_);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);

    const float char_w = font_size_px * 0.60f;
    const float char_h = font_size_px;

    const bool has_tilt = (
        tilt_deg != 0.0f &&
        container_rect[2] > 0.0f &&
        container_rect[3] > 0.0f);

    const float cx0 = container_rect[0];
    const float cy0 = container_rect[1];
    const float cw  = container_rect[2];
    const float ch  = container_rect[3];
    const float cx_center = cx0 + cw * 0.5f;

    constexpr float kDegToRad = 3.14159265358979323846f / 180.0f;
    float dx = 0.0f;
    if (has_tilt) {
        dx = ch * std::tan(tilt_deg * kDegToRad);
        dx = std::clamp(dx, -cw * 0.45f, cw * 0.45f);
    }

    auto TransformVertex = [&](float vx, float vy) -> std::pair<float, float> {
        if (!has_tilt) return {vx, vy};
        float t = std::clamp((vy - cy0) / ch, 0.0f, 1.0f);
        float s = 1.0f - (1.0f - t) * (2.0f * dx / cw);
        float nx = cx_center + (vx - cx_center) * s;
        float ny = (cy0 + ch) - ((cy0 + ch) - vy) * s;
        return {nx, ny};
    };

    auto GetAlphaScale = [&](float vy) -> float {
        if (!has_tilt) return 1.0f;
        float t = (vy - cy0) / ch;
        if (t < 0.25f) {
            return std::clamp(t / 0.25f, 0.0f, 1.0f);
        }
        return 1.0f;
    };

    const float alpha_top = color_rgba[3] * GetAlphaScale(y);
    const float alpha_bot = color_rgba[3] * GetAlphaScale(y + char_h);

    glBegin(GL_QUADS);
    float cur_x = x;
    for (char c : text) {
        if (c < 32 || c > 126) c = ' ';
        int char_idx = c - 32;
        int col = char_idx % 16;
        int row = char_idx / 16;

        float u0 = (col * 8.0f) / 128.0f;
        float v0 = (row * 8.0f) / 128.0f;
        float u1 = ((col + 1) * 8.0f) / 128.0f;
        float v1 = ((row + 1) * 8.0f) / 128.0f;

        auto [x0, y0] = TransformVertex(cur_x, y);
        auto [x1, y1] = TransformVertex(cur_x + char_w, y);
        auto [x2, y2] = TransformVertex(cur_x + char_w, y + char_h);
        auto [x3, y3] = TransformVertex(cur_x, y + char_h);

        glColor4f(color_rgba[0], color_rgba[1], color_rgba[2], alpha_top);
        glTexCoord2f(u0, v0); glVertex2f(x0, y0);
        glTexCoord2f(u1, v0); glVertex2f(x1, y1);

        glColor4f(color_rgba[0], color_rgba[1], color_rgba[2], alpha_bot);
        glTexCoord2f(u1, v1); glVertex2f(x2, y2);
        glTexCoord2f(u0, v1); glVertex2f(x3, y3);

        cur_x += char_w;
    }
    glEnd();

    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_TEXTURE_2D);
}

void FontRenderer::DrawRapidFireEffect(
    const std::array<float, 4>& pixel_rect,
    const float base_color_rgba[4],
    int64_t current_time_ms) {
    float bright_rgba[4] = {
        std::min(1.0f, base_color_rgba[0] * 1.4f + 0.3f),
        std::min(1.0f, base_color_rgba[1] * 1.4f + 0.3f),
        std::min(1.0f, base_color_rgba[2] * 1.4f + 0.3f),
        0.55f
    };
    glColor4f(bright_rgba[0], bright_rgba[1], bright_rgba[2], bright_rgba[3]);

    constexpr float kStripePeriod = 16.0f;
    constexpr float kStripeWidth = 2.5f;
    const float offset = std::fmod(
        static_cast<float>(current_time_ms) * 0.08f, kStripePeriod);

    glBegin(GL_QUADS);
    for (float sx = pixel_rect[0] + offset;
         sx < pixel_rect[0] + pixel_rect[2];
         sx += kStripePeriod) {
        float x1 = sx;
        float x2 = std::min(sx + kStripeWidth, pixel_rect[0] + pixel_rect[2]);
        glVertex2f(x1, pixel_rect[1]);
        glVertex2f(x2, pixel_rect[1]);
        glVertex2f(x2, pixel_rect[1] + pixel_rect[3]);
        glVertex2f(x1, pixel_rect[1] + pixel_rect[3]);
    }
    glEnd();
}

void FontRenderer::RenderText(
    const RenderCommand& cmd, int64_t current_time_ms) {
    if (cmd.text.empty()) return;

    float text_rgba[4]{};
    ParseHex(cmd.hex_color, text_rgba);

    std::string font_to_use =
        (cmd.font.empty() || cmd.font == "default")
            ? default_font_
            : cmd.font;

    BakedGlyphFont* font = nullptr;
    {
        std::lock_guard<std::mutex> lock(font_mutex_);
        font = GetOrLoadFontLocked(font_to_use);
    }
    const float total_w =
        MeasureText(cmd.text, font_to_use, cmd.font_size_px);

    float x = cmd.pixel_rect[0];
    if (cmd.alignment == "center") {
        x += std::max(0.0f, (cmd.pixel_rect[2] - total_w) * 0.5f);
    } else if (cmd.alignment == "right") {
        x += std::max(0.0f, cmd.pixel_rect[2] - total_w);
    }

    const float y = cmd.pixel_rect[1] +
        std::max(0.0f, (cmd.pixel_rect[3] - cmd.font_size_px) * 0.5f);

    auto DrawTextVariant = [&](float dx_offset, float dy_offset,
                               const float color[4]) {
        if (font != nullptr && font->is_valid) {
            DrawStringQuadsTTF(
                *font, cmd.text, x + dx_offset, y + dy_offset, cmd.font_size_px,
                color, cmd.tilt_deg, cmd.container_rect);
        } else {
            DrawStringQuadsFallback(
                cmd.text, x + dx_offset, y + dy_offset, cmd.font_size_px,
                color, cmd.tilt_deg, cmd.container_rect);
        }
    };

    // 1. Black outline if enabled
    if (cmd.black_outline) {
        constexpr float kOutlineBlack[4] = {0.0f, 0.0f, 0.0f, 1.0f};
        constexpr float kD = 1.5f;
        DrawTextVariant(-kD, 0.0f, kOutlineBlack);
        DrawTextVariant(+kD, 0.0f, kOutlineBlack);
        DrawTextVariant(0.0f, -kD, kOutlineBlack);
        DrawTextVariant(0.0f, +kD, kOutlineBlack);
    }

    // 2. Main text
    DrawTextVariant(0.0f, 0.0f, text_rgba);

    // 3. Rapid fire effect
    if (cmd.rapid_fire_effect) {
        DrawRapidFireEffect(
            {x, y, total_w, cmd.font_size_px}, text_rgba, current_time_ms);
    }
}

}  // namespace live_renderer
