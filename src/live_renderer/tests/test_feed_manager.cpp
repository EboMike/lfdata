#include <gtest/gtest.h>

#include <cstdio>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "live_renderer/config/config_serializer.hpp"
#include "live_renderer/config/global_config.hpp"
#include "live_renderer/feeds/rtsp_feed_reader.hpp"
#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/windows/feed_manager_window.hpp"
#include "live_renderer/windows/main_control_window.hpp"

namespace {

using namespace live_renderer;

class FakeFeedReader : public IFeedReader {
public:
    bool simulate_error = false;
    std::string simulated_error_msg = "Simulated connection failure";
    int open_calls = 0;
    int close_calls = 0;

    bool Open(const std::string& url) override {
        ++open_calls;
        url_ = url;
        std::string err;
        if (!RtspFeedReader::ValidateRtspUrl(url, err)) {
            state_ = FeedConnectionState::kError;
            error_ = err;
            return false;
        }
        if (simulate_error) {
            state_ = FeedConnectionState::kError;
            error_ = simulated_error_msg;
            return false;
        }
        state_ = FeedConnectionState::kConnected;
        error_.clear();
        width_ = 640;
        height_ = 360;
        frame_rgba_.assign(static_cast<size_t>(width_) * height_ * 4, 255);
        seq_ = 1;
        return true;
    }

    void Close() override {
        ++close_calls;
        state_ = FeedConnectionState::kDisconnected;
        frame_rgba_.clear();
    }

    bool IsOpen() const override {
        return state_ == FeedConnectionState::kConnecting ||
               state_ == FeedConnectionState::kConnected;
    }

    FeedConnectionState GetState() const override { return state_; }
    std::string GetErrorMessage() const override { return error_; }
    std::string GetUrl() const override { return url_; }
    int GetWidth() const override { return width_; }
    int GetHeight() const override { return height_; }
    uint64_t GetFrameSequence() const override { return seq_; }

    bool CopyLatestFrameRgba(
        std::vector<uint8_t>& out_rgba,
        int& out_width,
        int& out_height,
        uint64_t& in_out_seq) const override {
        if (seq_ == 0 || seq_ == in_out_seq || frame_rgba_.empty()) {
            return false;
        }
        out_rgba = frame_rgba_;
        out_width = width_;
        out_height = height_;
        in_out_seq = seq_;
        return true;
    }

private:
    std::string url_;
    FeedConnectionState state_ = FeedConnectionState::kDisconnected;
    std::string error_;
    int width_ = 0;
    int height_ = 0;
    uint64_t seq_ = 0;
    std::vector<uint8_t> frame_rgba_;
};

TEST(RtspFeedReaderTest, ValidatesRtspUrls) {
    std::string err;
    EXPECT_TRUE(RtspFeedReader::ValidateRtspUrl("rtsp://192.168.1.50/stream", err));
    EXPECT_TRUE(err.empty());
    EXPECT_TRUE(RtspFeedReader::ValidateRtspUrl("rtsps://user:pass@cam.local:554/live", err));
    EXPECT_TRUE(RtspFeedReader::ValidateRtspUrl("RTSP://[::1]:8554/test", err));

    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("", err));
    EXPECT_FALSE(err.empty());
    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("http://192.168.1.50/stream", err));
    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("rtsp://", err));
    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("rtsp://cam.local:99999/live", err));
    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("rtsp://cam.local:abc/live", err));
    EXPECT_FALSE(RtspFeedReader::ValidateRtspUrl("rtsp://cam local/live", err));
}

TEST(FeedManagerWindowTest, ComputesGridColumnsWithMinimum320pxWidth) {
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(0.0f), 1);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(319.0f), 1);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(320.0f), 1);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(639.0f), 1);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(640.0f), 2);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(960.0f), 3);
    EXPECT_EQ(FeedManagerWindow::ComputeGridColumns(1280.0f), 4);
}

TEST(FeedManagerWindowTest, AddEditAndRemoveFeeds) {
    std::vector<FeedConfig> feeds;
    FeedManagerWindow mgr(feeds, []() {
        return std::make_unique<FakeFeedReader>();
    });

    int changed_count = 0;
    mgr.SetCallbacks({
        .on_feeds_changed = [&](const std::vector<FeedConfig>&) { ++changed_count; }
    });

    // Add dialog validation rejects invalid URL and empty name
    mgr.OpenAddFeedDialog();
    EXPECT_TRUE(mgr.IsFeedDialogOpen());
    EXPECT_FALSE(mgr.IsEditingExistingFeed());

    mgr.SetDialogFields("Arena Cam 1", "http://not-rtsp/stream");
    EXPECT_FALSE(mgr.ValidateAndConnectDialogUrl());
    EXPECT_FALSE(mgr.GetDialogError().empty());
    EXPECT_FALSE(mgr.ConfirmFeedDialog());
    EXPECT_EQ(feeds.size(), 0u);

    // Valid URL connects and confirms
    mgr.SetDialogFields("Arena Cam 1", "rtsp://10.0.0.10:554/stream1");
    EXPECT_TRUE(mgr.ValidateAndConnectDialogUrl());
    EXPECT_TRUE(mgr.GetDialogError().empty());
    EXPECT_EQ(mgr.GetDialogConnectionState(), FeedConnectionState::kConnected);
    EXPECT_TRUE(mgr.ConfirmFeedDialog());
    EXPECT_FALSE(mgr.IsFeedDialogOpen());
    ASSERT_EQ(feeds.size(), 1u);
    EXPECT_EQ(feeds[0].name, "Arena Cam 1");
    EXPECT_EQ(feeds[0].url, "rtsp://10.0.0.10:554/stream1");
    EXPECT_EQ(changed_count, 1);

    // Edit existing feed
    mgr.OpenEditFeedDialog(0);
    EXPECT_TRUE(mgr.IsFeedDialogOpen());
    EXPECT_TRUE(mgr.IsEditingExistingFeed());
    EXPECT_EQ(mgr.GetDialogName(), "Arena Cam 1");
    EXPECT_EQ(mgr.GetDialogUrl(), "rtsp://10.0.0.10:554/stream1");

    mgr.SetDialogFields("Main Arena", "rtsp://10.0.0.11:554/hd");
    EXPECT_TRUE(mgr.ConfirmFeedDialog());
    ASSERT_EQ(feeds.size(), 1u);
    EXPECT_EQ(feeds[0].name, "Main Arena");
    EXPECT_EQ(feeds[0].url, "rtsp://10.0.0.11:554/hd");
    EXPECT_EQ(changed_count, 2);

    // Remove existing feed
    mgr.OpenEditFeedDialog(0);
    EXPECT_TRUE(mgr.RemoveEditingFeed());
    EXPECT_FALSE(mgr.IsFeedDialogOpen());
    EXPECT_TRUE(feeds.empty());
    EXPECT_EQ(changed_count, 3);
}

TEST(FeedManagerWindowTest, GlobalConfigSerializesFeeds) {
    const std::string temp_path = "test_global_config_feeds.yaml";
    GlobalConfig cfg;
    cfg.host = "127.0.0.1";
    cfg.port = 8001;
    cfg.feeds.push_back({"Cam A", "rtsp://192.168.1.10/live"});
    cfg.feeds.push_back({"Cam B", "rtsps://192.168.1.11:554/sub"});

    ASSERT_TRUE(ConfigSerializer::SaveGlobalConfig(temp_path, cfg));

    GlobalConfig loaded;
    ASSERT_TRUE(ConfigSerializer::LoadGlobalConfig(temp_path, loaded));
    ASSERT_EQ(loaded.feeds.size(), 2u);
    EXPECT_EQ(loaded.feeds[0].name, "Cam A");
    EXPECT_EQ(loaded.feeds[0].url, "rtsp://192.168.1.10/live");
    EXPECT_EQ(loaded.feeds[1].name, "Cam B");
    EXPECT_EQ(loaded.feeds[1].url, "rtsps://192.168.1.11:554/sub");

    std::filesystem::remove(temp_path);
}

TEST(FeedManagerWindowTest, MainControlWindowFeedsButtonTriggersCallback) {
    GlobalConfig global_cfg;
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_feeds.yaml", global_cfg, ui_cfg, store, client);
    bool feeds_opened = false;
    MainControlWindow::Callbacks cbs;
    cbs.on_open_feeds = [&]() { feeds_opened = true; };
    win.SetCallbacks(cbs);

    win.ClickFeeds();
    EXPECT_TRUE(feeds_opened);
}

}  // namespace
