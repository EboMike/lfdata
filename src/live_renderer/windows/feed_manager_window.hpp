/**
 * @file feed_manager_window.hpp
 * @brief Separate window managing live RTSP video feeds in a responsive grid.
 *
 * Displays configured RTSP feeds in a grid whose column count adapts to the
 * window width (minimum 320px per column), allows adding, editing, and removing
 * feeds via a modal dialog with live URL validation and connection preview, and
 * closes all active feed connections when the window is closed.
 */

#ifndef LIVE_RENDERER_WINDOWS_FEED_MANAGER_WINDOW_HPP_
#define LIVE_RENDERER_WINDOWS_FEED_MANAGER_WINDOW_HPP_

#include <SDL.h>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "live_renderer/config/global_config.hpp"
#include "live_renderer/feeds/rtsp_feed_reader.hpp"

struct ImGuiContext;

namespace live_renderer {

/**
 * @brief Window for viewing, adding, editing, and removing live RTSP feeds.
 */
class FeedManagerWindow {
public:
    static constexpr float kMinColumnWidth = 320.0f;

    struct Callbacks {
        std::function<void(const std::vector<FeedConfig>& feeds)> on_feeds_changed;
    };

    explicit FeedManagerWindow(
        std::vector<FeedConfig>& feeds,
        FeedReaderFactory reader_factory = nullptr);
    ~FeedManagerWindow();

    FeedManagerWindow(const FeedManagerWindow&) = delete;
    FeedManagerWindow& operator=(const FeedManagerWindow&) = delete;

    void SetCallbacks(Callbacks callbacks);
    void SetReaderFactory(FeedReaderFactory factory);

    /**
     * @brief Synchronizes active feed entries with the underlying feeds vector.
     */
    void SyncFeedsFromConfig();

    /**
     * @brief Opens the Feed Manager OS window and starts all configured feeds.
     *
     * @return True if opened (or already open), false if window creation failed.
     */
    bool Open();

    /**
     * @brief Closes the Feed Manager window and closes all active feed streams.
     */
    void Close();

    /**
     * @brief Returns true if the Feed Manager window is currently open.
     */
    bool IsOpen() const { return is_open_; }

    /**
     * @brief Processes an SDL event if it targets the Feed Manager window.
     *
     * @param event SDL event to inspect.
     * @return True if handled by the Feed Manager window.
     */
    bool HandleEvent(const SDL_Event& event);

    /**
     * @brief Renders one frame of the Feed Manager window if open.
     */
    void Render();

    /**
     * @brief Computes grid column count for a given available width in pixels.
     *
     * Ensures each column is at least 320 pixels wide (with a minimum of 1).
     */
    static int ComputeGridColumns(float available_width);

    // Programmatic / testable dialog & feed management API
    size_t GetFeedCount() const { return feeds_.size(); }
    bool IsAnyFeedOpen() const;
    FeedConnectionState GetFeedState(size_t index) const;

    void OpenAddFeedDialog();
    void OpenEditFeedDialog(size_t index);
    bool IsFeedDialogOpen() const { return show_feed_dialog_; }
    bool IsEditingExistingFeed() const { return editing_feed_index_ >= 0; }
    int GetEditingFeedIndex() const { return editing_feed_index_; }

    void SetDialogFields(const std::string& name, const std::string& url);
    std::string GetDialogName() const { return dialog_name_buf_; }
    std::string GetDialogUrl() const { return dialog_url_buf_; }
    std::string GetDialogError() const { return dialog_error_message_; }
    FeedConnectionState GetDialogConnectionState() const;

    /**
     * @brief Validates the current dialog URL and initiates connection preview.
     */
    bool ValidateAndConnectDialogUrl();

    /**
     * @brief Confirms the Add/Edit dialog, saving the feed on success.
     */
    bool ConfirmFeedDialog();

    /**
     * @brief Cancels the Add/Edit dialog without modifying feeds.
     */
    void CancelFeedDialog();

    /**
     * @brief Removes the currently edited feed and closes the dialog.
     */
    bool RemoveEditingFeed();

private:
    struct FeedRuntime {
        std::unique_ptr<IFeedReader> reader;
        unsigned int gl_texture_id = 0;
        int tex_width = 0;
        int tex_height = 0;
        uint64_t uploaded_seq = 0;
        std::vector<uint8_t> scratch_rgba;
    };

    std::unique_ptr<IFeedReader> CreateReader() const;
    void StartAllFeeds();
    void StopAllFeeds();
    void ReleaseRuntimeTexture(FeedRuntime& rt);
    void UploadLatestTextureIfNeeded(FeedRuntime& rt);

    void RenderGridContents();
    void RenderFeedDialog();
    void CloseFeedDialogInternal();

    std::vector<FeedConfig>& feeds_;
    FeedReaderFactory reader_factory_;
    Callbacks callbacks_;

    bool is_open_ = false;
    SDL_Window* sdl_window_ = nullptr;
    SDL_GLContext gl_context_ = nullptr;
    ImGuiContext* imgui_context_ = nullptr;
    uint32_t sdl_window_id_ = 0;

    std::vector<FeedRuntime> runtimes_;

    // Add/Edit feed dialog state
    bool show_feed_dialog_ = false;
    bool pending_open_feed_dialog_ = false;
    int editing_feed_index_ = -1;
    char dialog_name_buf_[256]{};
    char dialog_url_buf_[1024]{};
    std::string last_validated_url_;
    std::string dialog_error_message_;
    std::unique_ptr<IFeedReader> dialog_preview_reader_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_FEED_MANAGER_WINDOW_HPP_
