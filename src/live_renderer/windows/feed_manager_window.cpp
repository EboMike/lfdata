/**
 * @file feed_manager_window.cpp
 * @brief Implementation of FeedManagerWindow.
 */

#include "live_renderer/windows/feed_manager_window.hpp"

#include <SDL_opengl.h>
#include <imgui.h>
#include <imgui_impl_opengl3.h>
#include <imgui_impl_sdl2.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace live_renderer {

namespace {

constexpr int kDefaultWindowWidth = 720;
constexpr int kDefaultWindowHeight = 520;
constexpr float kCellAspectHeight = 9.0f / 16.0f;
constexpr float kCellFooterHeight = 28.0f;

std::string TrimCopy(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && (s[start] == ' ' || s[start] == '\t')) {
        ++start;
    }
    size_t end = s.size();
    while (end > start && (s[end - 1] == ' ' || s[end - 1] == '\t')) {
        --end;
    }
    return s.substr(start, end - start);
}

}  // namespace

FeedManagerWindow::FeedManagerWindow(
    std::vector<FeedConfig>& feeds,
    FeedReaderFactory reader_factory)
    : feeds_(feeds),
      reader_factory_(std::move(reader_factory)) {
    SyncFeedsFromConfig();
}

FeedManagerWindow::~FeedManagerWindow() {
    Close();
}

void FeedManagerWindow::SetCallbacks(Callbacks callbacks) {
    callbacks_ = std::move(callbacks);
}

void FeedManagerWindow::SetReaderFactory(FeedReaderFactory factory) {
    reader_factory_ = std::move(factory);
}

std::unique_ptr<IFeedReader> FeedManagerWindow::CreateReader() const {
    if (reader_factory_) {
        return reader_factory_();
    }
    return std::make_unique<RtspFeedReader>();
}

int FeedManagerWindow::ComputeGridColumns(float available_width) {
    if (available_width <= 0.0f) {
        return 1;
    }
    return std::max(1, static_cast<int>(std::floor(available_width / kMinColumnWidth)));
}

void FeedManagerWindow::SyncFeedsFromConfig() {
    StopAllFeeds();
    runtimes_.clear();
    runtimes_.resize(feeds_.size());
    if (is_open_) {
        StartAllFeeds();
    }
}

void FeedManagerWindow::StartAllFeeds() {
    if (runtimes_.size() != feeds_.size()) {
        runtimes_.resize(feeds_.size());
    }
    for (size_t i = 0; i < feeds_.size(); ++i) {
        if (!runtimes_[i].reader) {
            runtimes_[i].reader = CreateReader();
        }
        if (runtimes_[i].reader && !feeds_[i].url.empty()) {
            runtimes_[i].reader->Open(feeds_[i].url);
        }
    }
}

void FeedManagerWindow::StopAllFeeds() {
    if (dialog_preview_reader_) {
        dialog_preview_reader_->Close();
        dialog_preview_reader_.reset();
    }
    for (auto& rt : runtimes_) {
        if (rt.reader) {
            rt.reader->Close();
        }
        ReleaseRuntimeTexture(rt);
    }
}

void FeedManagerWindow::ReleaseRuntimeTexture(FeedRuntime& rt) {
    if (rt.gl_texture_id != 0 && gl_context_ && sdl_window_) {
        SDL_GL_MakeCurrent(sdl_window_, gl_context_);
        GLuint tex = static_cast<GLuint>(rt.gl_texture_id);
        glDeleteTextures(1, &tex);
    }
    rt.gl_texture_id = 0;
    rt.tex_width = 0;
    rt.tex_height = 0;
    rt.uploaded_seq = 0;
}

void FeedManagerWindow::UploadLatestTextureIfNeeded(FeedRuntime& rt) {
    if (!rt.reader) return;

    int w = 0;
    int h = 0;
    uint64_t seq = rt.uploaded_seq;
    if (!rt.reader->CopyLatestFrameRgba(rt.scratch_rgba, w, h, seq)) {
        return;
    }
    if (w <= 0 || h <= 0 || rt.scratch_rgba.empty()) {
        return;
    }

    if (rt.gl_texture_id == 0) {
        GLuint tex = 0;
        glGenTextures(1, &tex);
        rt.gl_texture_id = static_cast<unsigned int>(tex);
        glBindTexture(GL_TEXTURE_2D, tex);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    } else {
        glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(rt.gl_texture_id));
    }

    if (rt.tex_width != w || rt.tex_height != h) {
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            w,
            h,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            rt.scratch_rgba.data());
        rt.tex_width = w;
        rt.tex_height = h;
    } else {
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            w,
            h,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            rt.scratch_rgba.data());
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    rt.uploaded_seq = seq;
}

bool FeedManagerWindow::Open() {
    if (is_open_) {
        if (sdl_window_) {
            SDL_RaiseWindow(sdl_window_);
        }
        return true;
    }

    SDL_WindowFlags flags = static_cast<SDL_WindowFlags>(
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    sdl_window_ = SDL_CreateWindow(
        "LF Live Renderer - Feed Manager",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        kDefaultWindowWidth,
        kDefaultWindowHeight,
        flags);
    if (!sdl_window_) {
        return false;
    }

    sdl_window_id_ = SDL_GetWindowID(sdl_window_);
    gl_context_ = SDL_GL_CreateContext(sdl_window_);
    if (!gl_context_) {
        SDL_DestroyWindow(sdl_window_);
        sdl_window_ = nullptr;
        sdl_window_id_ = 0;
        return false;
    }

    SDL_GL_MakeCurrent(sdl_window_, gl_context_);
    SDL_GL_SetSwapInterval(1);

    ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
    imgui_context_ = ImGui::CreateContext();
    ImGui::SetCurrentContext(imgui_context_);
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    io.IniFilename = nullptr;
    ImGui::StyleColorsDark();
    ImGui_ImplSDL2_InitForOpenGL(sdl_window_, gl_context_);
    ImGui_ImplOpenGL3_Init("#version 330");
    ImGui::SetCurrentContext(prev_ctx);

    is_open_ = true;
    StartAllFeeds();
    return true;
}

void FeedManagerWindow::Close() {
    CloseFeedDialogInternal();
    StopAllFeeds();
    is_open_ = false;

    if (imgui_context_) {
        ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
        ImGui::SetCurrentContext(imgui_context_);
        if (gl_context_ && sdl_window_) {
            SDL_GL_MakeCurrent(sdl_window_, gl_context_);
        }
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplSDL2_Shutdown();
        ImGui::DestroyContext(imgui_context_);
        imgui_context_ = nullptr;
        if (prev_ctx != imgui_context_) {
            ImGui::SetCurrentContext(prev_ctx);
        }
    }

    if (gl_context_) {
        SDL_GL_DeleteContext(gl_context_);
        gl_context_ = nullptr;
    }
    if (sdl_window_) {
        SDL_DestroyWindow(sdl_window_);
        sdl_window_ = nullptr;
    }
    sdl_window_id_ = 0;
}

bool FeedManagerWindow::HandleEvent(const SDL_Event& event) {
    if (!is_open_ || !sdl_window_) {
        return false;
    }

    if (event.type == SDL_WINDOWEVENT &&
        event.window.windowID == sdl_window_id_ &&
        event.window.event == SDL_WINDOWEVENT_CLOSE) {
        Close();
        return true;
    }

    bool belongs_to_window = false;
    if (event.type == SDL_WINDOWEVENT && event.window.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEMOTION && event.motion.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP) &&
               event.button.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_MOUSEWHEEL && event.wheel.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if ((event.type == SDL_KEYDOWN || event.type == SDL_KEYUP) &&
               event.key.windowID == sdl_window_id_) {
        belongs_to_window = true;
    } else if (event.type == SDL_TEXTINPUT && event.text.windowID == sdl_window_id_) {
        belongs_to_window = true;
    }

    if (belongs_to_window && imgui_context_) {
        ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
        ImGui::SetCurrentContext(imgui_context_);
        ImGui_ImplSDL2_ProcessEvent(&event);
        ImGui::SetCurrentContext(prev_ctx);
        return true;
    }

    return false;
}

void FeedManagerWindow::Render() {
    if (!is_open_ || !sdl_window_ || !gl_context_ || !imgui_context_) {
        return;
    }

    SDL_GL_MakeCurrent(sdl_window_, gl_context_);
    ImGuiContext* prev_ctx = ImGui::GetCurrentContext();
    ImGui::SetCurrentContext(imgui_context_);

    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplSDL2_NewFrame();
    ImGui::NewFrame();

    const ImGuiViewport* viewport = ImGui::GetMainViewport();
    ImGui::SetNextWindowPos(viewport->WorkPos);
    ImGui::SetNextWindowSize(viewport->WorkSize);

    constexpr ImGuiWindowFlags kWindowFlags =
        ImGuiWindowFlags_NoDecoration |
        ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings;

    if (ImGui::Begin("Feed Manager", nullptr, kWindowFlags)) {
        RenderGridContents();
        RenderFeedDialog();
    }
    ImGui::End();

    ImGui::Render();
    int display_w = 0;
    int display_h = 0;
    SDL_GL_GetDrawableSize(sdl_window_, &display_w, &display_h);
    glViewport(0, 0, display_w, display_h);
    glClearColor(0.08f, 0.09f, 0.11f, 1.00f);
    glClear(GL_COLOR_BUFFER_BIT);
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    SDL_GL_SwapWindow(sdl_window_);

    ImGui::SetCurrentContext(prev_ctx);
}

void FeedManagerWindow::RenderGridContents() {
    const float button_height = 36.0f;
    const float footer_reserve = button_height + ImGui::GetStyle().ItemSpacing.y * 2.0f;
    const float grid_height = std::max(100.0f, ImGui::GetContentRegionAvail().y - footer_reserve);

    ImGui::BeginChild("##FeedGridScroll", ImVec2(0.0f, grid_height), false);

    const float avail_w = ImGui::GetContentRegionAvail().x;
    const int columns = ComputeGridColumns(avail_w);
    const float spacing_x = ImGui::GetStyle().ItemSpacing.x;
    const float col_w = std::max(
        kMinColumnWidth,
        (avail_w - spacing_x * static_cast<float>(columns - 1)) /
            static_cast<float>(columns));
    const float video_h = col_w * kCellAspectHeight;
    const float cell_h = video_h + kCellFooterHeight;

    if (feeds_.empty()) {
        const char* empty_msg = "No feeds configured. Click 'Add new feed' below.";
        const ImVec2 text_sz = ImGui::CalcTextSize(empty_msg);
        ImGui::SetCursorPosX(std::max(0.0f, (avail_w - text_sz.x) * 0.5f));
        ImGui::SetCursorPosY(std::max(0.0f, (grid_height - text_sz.y) * 0.5f));
        ImGui::TextDisabled("%s", empty_msg);
    } else if (ImGui::BeginTable("##FeedGridTable", columns, ImGuiTableFlags_None)) {
        for (size_t i = 0; i < feeds_.size(); ++i) {
            ImGui::TableNextColumn();
            ImGui::PushID(static_cast<int>(i));

            if (i < runtimes_.size()) {
                UploadLatestTextureIfNeeded(runtimes_[i]);
            }

            const ImVec2 cell_pos = ImGui::GetCursorScreenPos();
            if (ImGui::InvisibleButton("##FeedCellBtn", ImVec2(col_w, cell_h))) {
                OpenEditFeedDialog(i);
            }

            ImDrawList* draw_list = ImGui::GetWindowDrawList();
            const bool hovered = ImGui::IsItemHovered();
            const ImU32 bg_col = hovered
                ? IM_COL32(42, 46, 56, 255)
                : IM_COL32(28, 31, 38, 255);
            const ImU32 border_col = hovered
                ? IM_COL32(110, 155, 230, 255)
                : IM_COL32(65, 70, 82, 255);
            const ImVec2 cell_max(cell_pos.x + col_w, cell_pos.y + cell_h);
            draw_list->AddRectFilled(cell_pos, cell_max, bg_col, 4.0f);
            draw_list->AddRect(cell_pos, cell_max, border_col, 4.0f, 0, 1.5f);

            const float pad = 4.0f;
            const ImVec2 vid_min(cell_pos.x + pad, cell_pos.y + pad);
            const ImVec2 vid_max(cell_pos.x + col_w - pad, cell_pos.y + video_h);
            const float box_w = vid_max.x - vid_min.x;
            const float box_h = vid_max.y - vid_min.y;

            if (i < runtimes_.size() && runtimes_[i].gl_texture_id != 0 &&
                runtimes_[i].tex_width > 0 && runtimes_[i].tex_height > 0) {
                const float src_aspect =
                    static_cast<float>(runtimes_[i].tex_width) /
                    static_cast<float>(runtimes_[i].tex_height);
                const float dst_aspect = box_w / box_h;
                float draw_w = box_w;
                float draw_h = box_h;
                if (src_aspect > dst_aspect) {
                    draw_h = box_w / src_aspect;
                } else {
                    draw_w = box_h * src_aspect;
                }
                const float ox = vid_min.x + (box_w - draw_w) * 0.5f;
                const float oy = vid_min.y + (box_h - draw_h) * 0.5f;
                draw_list->AddImage(
                    static_cast<ImTextureID>(static_cast<intptr_t>(runtimes_[i].gl_texture_id)),
                    ImVec2(ox, oy),
                    ImVec2(ox + draw_w, oy + draw_h));
            } else {
                draw_list->AddRectFilled(vid_min, vid_max, IM_COL32(15, 17, 21, 255));
                std::string status_str = "Disconnected";
                ImU32 status_col = IM_COL32(160, 165, 175, 255);
                if (i < runtimes_.size() && runtimes_[i].reader) {
                    const FeedConnectionState st = runtimes_[i].reader->GetState();
                    if (st == FeedConnectionState::kConnecting) {
                        status_str = "Connecting...";
                        status_col = IM_COL32(220, 195, 90, 255);
                    } else if (st == FeedConnectionState::kError) {
                        status_str = "Connection Error";
                        status_col = IM_COL32(235, 90, 80, 255);
                    }
                }
                const ImVec2 st_sz = ImGui::CalcTextSize(status_str.c_str());
                draw_list->AddText(
                    ImVec2(
                        vid_min.x + (box_w - st_sz.x) * 0.5f,
                        vid_min.y + (box_h - st_sz.y) * 0.5f),
                    status_col,
                    status_str.c_str());
            }

            const std::string& label = feeds_[i].name.empty() ? feeds_[i].url : feeds_[i].name;
            const ImVec2 lbl_sz = ImGui::CalcTextSize(label.c_str());
            const float lbl_x = cell_pos.x + std::max(4.0f, (col_w - lbl_sz.x) * 0.5f);
            const float lbl_y = cell_pos.y + video_h +
                (kCellFooterHeight - lbl_sz.y) * 0.5f;
            draw_list->AddText(
                ImVec2(lbl_x, lbl_y),
                IM_COL32(235, 238, 245, 255),
                label.c_str());

            ImGui::PopID();
        }
        ImGui::EndTable();
    }

    ImGui::EndChild();

    ImGui::Spacing();
    if (ImGui::Button("Add new feed", ImVec2(ImGui::GetContentRegionAvail().x, button_height))) {
        OpenAddFeedDialog();
    }
}

void FeedManagerWindow::RenderFeedDialog() {
    if (pending_open_feed_dialog_) {
        ImGui::OpenPopup("Feed Settings");
        pending_open_feed_dialog_ = false;
    }

    if (!ImGui::BeginPopupModal("Feed Settings", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        return;
    }

    ImGui::TextUnformatted("Name:");
    ImGui::SetNextItemWidth(380.0f);
    ImGui::InputText("##FeedName", dialog_name_buf_, sizeof(dialog_name_buf_));

    ImGui::Spacing();
    ImGui::TextUnformatted("RTSP URL:");
    ImGui::SetNextItemWidth(380.0f);
    const bool submitted = ImGui::InputText(
        "##FeedUrl",
        dialog_url_buf_,
        sizeof(dialog_url_buf_),
        ImGuiInputTextFlags_EnterReturnsTrue);
    if (submitted || ImGui::IsItemDeactivatedAfterEdit()) {
        ValidateAndConnectDialogUrl();
    }

    // Status or error text underneath the URL field
    if (!dialog_error_message_.empty()) {
        ImGui::TextColored(
            ImVec4(0.95f, 0.30f, 0.25f, 1.0f),
            "%s",
            dialog_error_message_.c_str());
    } else if (dialog_preview_reader_) {
        const FeedConnectionState st = dialog_preview_reader_->GetState();
        if (st == FeedConnectionState::kConnecting) {
            ImGui::TextColored(ImVec4(0.90f, 0.80f, 0.35f, 1.0f), "Connecting...");
        } else if (st == FeedConnectionState::kConnected) {
            ImGui::TextColored(
                ImVec4(0.35f, 0.85f, 0.45f, 1.0f),
                "Connected (%dx%d)",
                dialog_preview_reader_->GetWidth(),
                dialog_preview_reader_->GetHeight());
        } else if (st == FeedConnectionState::kError) {
            const std::string err = dialog_preview_reader_->GetErrorMessage();
            ImGui::TextColored(
                ImVec4(0.95f, 0.30f, 0.25f, 1.0f),
                "%s",
                err.empty() ? "Unable to connect to RTSP stream." : err.c_str());
        }
    }

    ImGui::Spacing();
    ImGui::Separator();
    ImGui::Spacing();

    if (ImGui::Button("OK", ImVec2(110.0f, 0.0f))) {
        if (ConfirmFeedDialog()) {
            ImGui::CloseCurrentPopup();
        }
    }
    ImGui::SameLine();
    if (ImGui::Button("Cancel", ImVec2(110.0f, 0.0f))) {
        CancelFeedDialog();
        ImGui::CloseCurrentPopup();
    }
    if (IsEditingExistingFeed()) {
        ImGui::SameLine();
        if (ImGui::Button("Remove", ImVec2(110.0f, 0.0f))) {
            if (RemoveEditingFeed()) {
                ImGui::CloseCurrentPopup();
            }
        }
    }

    ImGui::EndPopup();
}

bool FeedManagerWindow::IsAnyFeedOpen() const {
    for (const auto& rt : runtimes_) {
        if (rt.reader && rt.reader->IsOpen()) {
            return true;
        }
    }
    return false;
}

FeedConnectionState FeedManagerWindow::GetFeedState(size_t index) const {
    if (index >= runtimes_.size() || !runtimes_[index].reader) {
        return FeedConnectionState::kDisconnected;
    }
    return runtimes_[index].reader->GetState();
}

void FeedManagerWindow::OpenAddFeedDialog() {
    CloseFeedDialogInternal();
    editing_feed_index_ = -1;
    dialog_name_buf_[0] = '\0';
    dialog_url_buf_[0] = '\0';
    last_validated_url_.clear();
    dialog_error_message_.clear();
    show_feed_dialog_ = true;
    pending_open_feed_dialog_ = true;
}

void FeedManagerWindow::OpenEditFeedDialog(size_t index) {
    if (index >= feeds_.size()) return;
    CloseFeedDialogInternal();
    editing_feed_index_ = static_cast<int>(index);
    std::snprintf(dialog_name_buf_, sizeof(dialog_name_buf_), "%s", feeds_[index].name.c_str());
    std::snprintf(dialog_url_buf_, sizeof(dialog_url_buf_), "%s", feeds_[index].url.c_str());
    last_validated_url_.clear();
    dialog_error_message_.clear();
    show_feed_dialog_ = true;
    pending_open_feed_dialog_ = true;
    ValidateAndConnectDialogUrl();
}

void FeedManagerWindow::SetDialogFields(const std::string& name, const std::string& url) {
    std::snprintf(dialog_name_buf_, sizeof(dialog_name_buf_), "%s", name.c_str());
    std::snprintf(dialog_url_buf_, sizeof(dialog_url_buf_), "%s", url.c_str());
}

FeedConnectionState FeedManagerWindow::GetDialogConnectionState() const {
    if (!dialog_preview_reader_) {
        return FeedConnectionState::kDisconnected;
    }
    return dialog_preview_reader_->GetState();
}

bool FeedManagerWindow::ValidateAndConnectDialogUrl() {
    const std::string url = TrimCopy(dialog_url_buf_);
    std::string err;
    if (!RtspFeedReader::ValidateRtspUrl(url, err)) {
        dialog_error_message_ = err;
        if (dialog_preview_reader_) {
            dialog_preview_reader_->Close();
            dialog_preview_reader_.reset();
        }
        last_validated_url_.clear();
        return false;
    }

    dialog_error_message_.clear();
    if (url == last_validated_url_ && dialog_preview_reader_ &&
        dialog_preview_reader_->IsOpen()) {
        return true;
    }

    last_validated_url_ = url;
    if (!dialog_preview_reader_) {
        dialog_preview_reader_ = CreateReader();
    } else {
        dialog_preview_reader_->Close();
    }

    if (dialog_preview_reader_ && !dialog_preview_reader_->Open(url)) {
        dialog_error_message_ = dialog_preview_reader_->GetErrorMessage();
        return false;
    }
    return true;
}

bool FeedManagerWindow::ConfirmFeedDialog() {
    const std::string name = TrimCopy(dialog_name_buf_);
    const std::string url = TrimCopy(dialog_url_buf_);

    if (name.empty()) {
        dialog_error_message_ = "Feed name cannot be empty.";
        return false;
    }

    std::string url_err;
    if (!RtspFeedReader::ValidateRtspUrl(url, url_err)) {
        dialog_error_message_ = url_err;
        return false;
    }

    FeedConfig cfg{name, url};
    if (editing_feed_index_ >= 0 &&
        editing_feed_index_ < static_cast<int>(feeds_.size())) {
        const size_t idx = static_cast<size_t>(editing_feed_index_);
        feeds_[idx] = cfg;
        if (idx < runtimes_.size()) {
            if (runtimes_[idx].reader) {
                runtimes_[idx].reader->Close();
            }
            ReleaseRuntimeTexture(runtimes_[idx]);
            if (is_open_) {
                if (!runtimes_[idx].reader) {
                    runtimes_[idx].reader = CreateReader();
                }
                if (runtimes_[idx].reader) {
                    runtimes_[idx].reader->Open(cfg.url);
                }
            }
        }
    } else {
        feeds_.push_back(cfg);
        FeedRuntime rt;
        if (is_open_) {
            rt.reader = CreateReader();
            if (rt.reader) {
                rt.reader->Open(cfg.url);
            }
        }
        runtimes_.push_back(std::move(rt));
    }

    CloseFeedDialogInternal();
    if (callbacks_.on_feeds_changed) {
        callbacks_.on_feeds_changed(feeds_);
    }
    return true;
}

void FeedManagerWindow::CancelFeedDialog() {
    CloseFeedDialogInternal();
}

bool FeedManagerWindow::RemoveEditingFeed() {
    if (editing_feed_index_ < 0 ||
        editing_feed_index_ >= static_cast<int>(feeds_.size())) {
        return false;
    }

    const size_t idx = static_cast<size_t>(editing_feed_index_);
    if (idx < runtimes_.size()) {
        if (runtimes_[idx].reader) {
            runtimes_[idx].reader->Close();
        }
        ReleaseRuntimeTexture(runtimes_[idx]);
        runtimes_.erase(runtimes_.begin() + static_cast<ptrdiff_t>(idx));
    }
    feeds_.erase(feeds_.begin() + static_cast<ptrdiff_t>(idx));

    CloseFeedDialogInternal();
    if (callbacks_.on_feeds_changed) {
        callbacks_.on_feeds_changed(feeds_);
    }
    return true;
}

void FeedManagerWindow::CloseFeedDialogInternal() {
    if (dialog_preview_reader_) {
        dialog_preview_reader_->Close();
        dialog_preview_reader_.reset();
    }
    show_feed_dialog_ = false;
    pending_open_feed_dialog_ = false;
    editing_feed_index_ = -1;
    last_validated_url_.clear();
    dialog_error_message_.clear();
}

}  // namespace live_renderer
